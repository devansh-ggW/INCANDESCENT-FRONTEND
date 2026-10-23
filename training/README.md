# Photon 1 model-improvement lab

This directory contains **real, repeatable tooling** for improving the weights behind Photon 1. It is separate from the Incandescent application prompt and agent code.

## Important hardware reality

The current target PC (Intel i3-3240, 8 GB system RAM, integrated graphics) does not have a CUDA GPU. It can run the quantized Ollama model for inference, but it is not a practical machine for LoRA/QLoRA fine-tuning a 1.54B-parameter Transformers model: the full training stack, optimizer states/activations, and framework overhead are larger than its available memory budget and CPU throughput is extremely poor. The training script deliberately refuses to start without a CUDA GPU rather than swap the machine into an unusable state.

This is not a pretend fine-tune. The app has **not** changed Photon 1's weights yet. On compatible CUDA hardware, this tooling can train an adapter and produce logs/checkpoints; using the adapter in Ollama then requires merging/conversion to a compatible GGUF and a separate model profile.

## Workflow

0. Before installing heavyweight packages, run `python training/check_hardware.py`. It uses the standard library to report host RAM and NVIDIA VRAM. The current CPU-only 8 GB target should stop here and use the app for inference, project analysis, test-driven work, and evaluation instead.
1. Add examples you own or have a documented license/permission to use to `training/data/raw.jsonl`. Each line is JSON with `instruction`, `response`, `category`, `source`, and `license`. Review every answer and verify rights before training.
2. Validate, deduplicate, and split examples:

   ```bash
   python training/prepare_dataset.py training/data/raw.jsonl --out-dir training/data/split --min-examples 30
   ```

   It writes `train.jsonl`, `validation.jsonl`, `test.jsonl`, plus a manifest. Test data is never passed to the training script.
3. Install the training dependencies on a CUDA-compatible machine using `pip install -r training/requirements.txt`.
4. Train an adapter with LoRA:

   ```bash
   python training/train_lora.py --data-dir training/data/split --output-root training/output
   ```

   Add `--qlora` only on a supported CUDA setup with `bitsandbytes` installed. Default GPU guard requires enough free VRAM and is intentionally conservative.
5. Run the exact same evaluation cases before and after training with `python evaluation/run_eval.py --model photon1 --output evaluation/results/baseline.json`, then select the candidate Ollama model/adapter and run again to a different output path. Compare outputs, latency, and heuristic checks; manually inspect code correctness too. The fine-tune script also records a small `heldout-generations.jsonl` file in the adapter output folder for direct reference-versus-candidate review. It is evidence for human review, not an automatic correctness score.
6. Keep the adapter only if held-out quality improves without clear regressions. Keep the original model and prior adapters for rollback.

## Dataset rules

Use small, correct, diverse examples: normal code generation, debugging with corrected code, tests, multi-file reasoning, instruction following, and concise conversational behavior. Include source/license metadata. Do not ingest arbitrary scraped repositories, secrets, benchmark answers, or unverified model-generated completions. Have a human inspect every example. The handful of examples under `training/data/schema_examples.jsonl` demonstrate format only; they are **not a useful training corpus** and are intentionally too small to train on. The split tool keeps normalized identical instructions within a single split so repeated prompts cannot leak directly between training and held-out test data.
