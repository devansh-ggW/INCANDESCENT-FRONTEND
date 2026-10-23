#!/usr/bin/env python3
"""Train a Photon 1 LoRA adapter on supported CUDA hardware; CPU-only is refused."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

def read_jsonl(path: Path):
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip(): continue
        try: row = json.loads(line)
        except json.JSONDecodeError as exc: raise ValueError(f"{path}:{number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row.get("instruction"), str) or not isinstance(row.get("response"), str):
            raise ValueError(f"{path}:{number}: expected instruction and response strings")
        rows.append(row)
    return rows

def pack_training_example(prompt_ids, answer_ids, max_seq_length, eos_token_id=None):
    """Pack prompt + answer while always preserving a supervised answer target.

    Older code truncated the concatenated sample from the right. For long prompts,
    that could erase the entire answer while leaving a zero-loss training example.
    Keep the final conversational context and reserve explicit capacity for the target.
    """
    if max_seq_length < 8:
        raise ValueError("max_seq_length must be at least 8")
    prompt = list(prompt_ids or [])
    answer = list(answer_ids or [])
    if not answer:
        raise ValueError("training response tokenized to an empty sequence")
    answer_budget = max(4, min(max_seq_length - 2, int(max_seq_length * 0.65)))
    if eos_token_id is not None:
        if answer and answer[-1] == eos_token_id:
            answer = answer[:-1]
        if len(answer) >= answer_budget:
            answer = answer[:answer_budget - 1] + [eos_token_id]
        else:
            answer.append(eos_token_id)
    else:
        answer = answer[:answer_budget]
    prompt_budget = max_seq_length - len(answer)
    if prompt_budget < 1:
        answer = answer[:max_seq_length - 1]
        prompt_budget = 1
    if len(prompt) > prompt_budget:
        # Keep the BOS/control prefix where possible and retain the most recent
        # user/task tokens near the generation boundary.
        if prompt_budget == 1:
            prompt = prompt[-1:]
        else:
            prompt = prompt[:1] + prompt[-(prompt_budget - 1):]
    input_ids = prompt + answer
    labels = ([-100] * len(prompt)) + answer.copy()
    input_ids = input_ids[:max_seq_length]
    labels = labels[:max_seq_length]
    if len(input_ids) != len(labels) or not any(label != -100 for label in labels):
        raise ValueError("packing failed to preserve supervised answer tokens")
    return {"input_ids": input_ids, "attention_mask": [1] * len(input_ids), "labels": labels}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path("training/data/split"))
    ap.add_argument("--output-root", type=Path, default=Path("training/output"))
    ap.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--learning-rate", type=float, default=8e-5)
    ap.add_argument("--max-seq-length", type=int, default=768)
    ap.add_argument("--max-heldout-samples", type=int, default=12, help="Save manual-review generations from this many held-out test items")
    ap.add_argument("--test-max-new-tokens", type=int, default=192)
    ap.add_argument("--qlora", action="store_true", help="Use bitsandbytes 4-bit loading when compatible")
    ap.add_argument("--confirm-training-data-reviewed", action="store_true", help="Confirm examples and licenses were manually reviewed")
    args = ap.parse_args()
    train_path, val_path, test_path = (args.data_dir / f"{name}.jsonl" for name in ("train", "validation", "test"))
    if not all(path.exists() for path in (train_path, val_path, test_path)):
        print("STOP: missing train/validation/test split. Run prepare_dataset.py first.", file=sys.stderr); return 2
    train_rows, val_rows, test_rows = read_jsonl(train_path), read_jsonl(val_path), read_jsonl(test_path)
    if len(train_rows) < 25 or len(val_rows) < 2 or len(test_rows) < 2:
        print("STOP: split too small for a responsible fine-tune. Use >=30 valid examples plus validation/test examples; hundreds or more curated examples are preferable.", file=sys.stderr); return 2
    if not args.confirm_training_data_reviewed:
        print("STOP: review data correctness and licensing, then pass --confirm-training-data-reviewed.", file=sys.stderr); return 2
    if args.epochs <= 0 or args.learning_rate <= 0:
        print("STOP: epochs and learning rate must be positive.", file=sys.stderr); return 2
    if not 1 <= args.max_heldout_samples <= 100 or not 16 <= args.test_max_new_tokens <= 1024:
        print("STOP: held-out sample count must be 1–100 and test generation must be 16–1024 tokens.", file=sys.stderr); return 2
    try:
        import torch
    except Exception as exc:
        print(f"STOP: PyTorch is not installed: {exc}. Install training/requirements.txt on a compatible machine.", file=sys.stderr); return 2
    if not torch.cuda.is_available():
        print("STOP: no CUDA GPU detected. The current 8 GB CPU-only PC cannot reliably fine-tune this 1.5B model. Training was not started and no weights were changed.", file=sys.stderr); return 2
    try:
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq, Trainer, TrainingArguments
    except Exception as exc:
        print(f"STOP: training dependency missing: {exc}. Install training/requirements.txt on compatible CUDA hardware.", file=sys.stderr); return 2
    free_bytes, total_bytes = torch.cuda.mem_get_info()
    free_gib = free_bytes / (1024**3)
    if free_gib < 7.0:
        print(f"STOP: only {free_gib:.1f} GiB GPU memory is free. At least 7 GiB free is required by this guarded configuration; 10+ GiB is safer.", file=sys.stderr); return 2
    if args.max_seq_length < 128 or args.max_seq_length > 2048:
        print("STOP: max-seq-length must be 128–2048 for this low-memory recipe.", file=sys.stderr); return 2
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=False)
    if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token
    load_args = {"torch_dtype": torch.float16, "device_map": "auto", "low_cpu_mem_usage": True, "trust_remote_code": False}
    if args.qlora:
        try:
            from transformers import BitsAndBytesConfig
            load_args["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
        except Exception as exc:
            print(f"STOP: QLoRA setup failed or bitsandbytes is unsupported: {exc}", file=sys.stderr); return 2
    model = AutoModelForCausalLM.from_pretrained(args.base_model, **load_args)
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    if args.qlora: model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM", target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    model.print_trainable_parameters()

    def prompt_ids_for(row):
        system = row.get("system", "You are Photon 1, a precise and naturally conversational coding assistant inside Incandescent. Produce correct, usable code; infer sensible defaults; do not claim tests you did not run.")
        return tokenizer.apply_chat_template([{"role":"system","content":system},{"role":"user","content":row["instruction"]}], tokenize=True, add_generation_prompt=True)

    def encode(row):
        prompt = prompt_ids_for(row)
        answer = tokenizer.encode(row["response"], add_special_tokens=False)
        return pack_training_example(prompt, answer, args.max_seq_length, tokenizer.eos_token_id)

    train_ds = Dataset.from_list([encode(row) for row in train_rows])
    val_ds = Dataset.from_list([encode(row) for row in val_rows])
    stamp = time.strftime("%Y%m%d-%H%M%S")
    output = args.output_root / ("photon1-lora-" + stamp)
    output.mkdir(parents=True, exist_ok=False)
    (output / "run-config.json").write_text(json.dumps({"base_model":args.base_model,"epochs":args.epochs,"learning_rate":args.learning_rate,"max_seq_length":args.max_seq_length,"train_examples":len(train_rows),"validation_examples":len(val_rows),"held_out_test_examples":len(test_rows),"qlora":args.qlora,"free_vram_gib_at_start":round(free_gib,2),"test_set_used_for_training":False},indent=2),encoding="utf-8")
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100, return_tensors="pt")
    training_args = TrainingArguments(output_dir=str(output / "checkpoints"), num_train_epochs=args.epochs, learning_rate=args.learning_rate, per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=8, gradient_checkpointing=True, fp16=True, logging_steps=5, eval_strategy="epoch", save_strategy="epoch", save_total_limit=2, load_best_model_at_end=True, metric_for_best_model="eval_loss", greater_is_better=False, report_to="none", dataloader_num_workers=0, optim="adamw_torch", warmup_ratio=0.05)
    trainer = Trainer(model=model, args=training_args, train_dataset=train_ds, eval_dataset=val_ds, data_collator=collator)
    result = trainer.train()
    trainer.save_model(str(output / "adapter"))
    tokenizer.save_pretrained(str(output / "tokenizer"))
    evaluation = trainer.evaluate()

    # Generate a small held-out review set after training. This is evidence for
    # a human evaluator, not an automatic correctness score and not training data.
    import torch
    heldout_path = output / "heldout-generations.jsonl"
    model.eval()
    heldout_results = []
    for row in test_rows[:args.max_heldout_samples]:
        record = {"instruction": row["instruction"], "reference_response": row["response"], "generated_response": "", "error": None}
        try:
            ids = prompt_ids_for(row)
            max_prompt = max(32, args.max_seq_length - min(args.test_max_new_tokens, args.max_seq_length // 2))
            if len(ids) > max_prompt:
                ids = ids[:1] + ids[-(max_prompt - 1):]
            input_tensor = torch.tensor([ids], dtype=torch.long, device=model.get_input_embeddings().weight.device)
            with torch.no_grad():
                generated = model.generate(input_ids=input_tensor, attention_mask=torch.ones_like(input_tensor), max_new_tokens=args.test_max_new_tokens, do_sample=False, eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id)
            record["generated_response"] = tokenizer.decode(generated[0][len(ids):], skip_special_tokens=True)
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        heldout_results.append(record)
        with heldout_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    result_summary = {"training_metrics": result.metrics, "validation_metrics": evaluation, "trainable_parameter_summary": "See the console logs above", "held_out_test_count": len(test_rows), "held_out_samples_generated": len(heldout_results), "held_out_generation_errors": sum(1 for row in heldout_results if row["error"]), "held_out_test_used_for_training": False, "adapter_path": str(output / "adapter"), "heldout_review_file": str(heldout_path), "note": "Inspect heldout-generations.jsonl manually, run the same evaluation/run_eval.py cases against the base and candidate models, and run code tests before claiming improvement. Adapter is not an Ollama GGUF."}
    (output / "result.json").write_text(json.dumps(result_summary, indent=2, default=float), encoding="utf-8")
    print(json.dumps(result_summary, indent=2, default=float))
    return 0

if __name__ == "__main__": raise SystemExit(main())
