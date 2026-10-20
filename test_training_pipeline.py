#!/usr/bin/env python3
"""Offline unit tests for Photon 1's dataset and supervised packing safeguards."""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'training'))
from train_lora import pack_training_example
from prepare_dataset import load_rows
from check_hardware import classify_training_hardware


class SupervisedPackingTests(unittest.TestCase):
    def test_long_prompt_preserves_supervised_answer(self):
        packed = pack_training_example(list(range(1000)), list(range(2000, 2100)), 128, eos_token_id=2)
        self.assertLessEqual(len(packed['input_ids']), 128)
        self.assertEqual(len(packed['input_ids']), len(packed['labels']))
        supervised = [token for token in packed['labels'] if token != -100]
        self.assertGreater(len(supervised), 1)
        self.assertEqual(supervised[-1], 2)

    def test_long_answer_is_capped_but_not_erased(self):
        packed = pack_training_example([1, 2, 3], list(range(1000, 2000)), 128, eos_token_id=2)
        self.assertLessEqual(len(packed['input_ids']), 128)
        self.assertEqual(len(packed['input_ids']), len(packed['labels']))
        self.assertEqual(packed['labels'][:3], [-100, -100, -100])
        self.assertTrue(all(label != -100 for label in packed['labels'][3:]))
        self.assertEqual(packed['labels'][-1], 2)

    def test_empty_target_is_rejected(self):
        with self.assertRaises(ValueError):
            pack_training_example([1, 2], [], 128, eos_token_id=2)


class HardwareGuardTests(unittest.TestCase):
    def test_cpu_only_machine_is_blocked_before_training(self):
        status, note = classify_training_hardware(8.0, 3.0, [])
        self.assertEqual(status, "blocked")
        self.assertIn("No NVIDIA CUDA GPU", note)

    def test_small_gpu_memory_is_blocked(self):
        status, note = classify_training_hardware(32.0, 20.0, [{"name":"Test GPU", "free_gib":4.0, "total_gib":8.0}])
        self.assertEqual(status, "blocked")
        self.assertIn("7 GiB", note)

    def test_suitable_hardware_is_only_a_candidate(self):
        status, note = classify_training_hardware(32.0, 20.0, [{"name":"Test GPU", "free_gib":12.0, "total_gib":16.0}])
        self.assertEqual(status, "candidate")
        self.assertIn("not a guarantee", note)


class DatasetSplitTests(unittest.TestCase):
    def test_short_categories_and_instruction_group_leakage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'raw.jsonl'
            rows = []
            for i in range(40):
                rows.append({"instruction":f"Task number {i} please implement this", "response":f"Response number {i} with usable explanation", "category":"js", "source":"self-authored", "license":"CC0-1.0"})
            rows.extend([
                {"instruction":"Same task should stay in one split", "response":"First valid answer to this same task", "category":"qa", "source":"self-authored", "license":"CC0-1.0"},
                {"instruction":"  SAME   TASK should stay in one split ", "response":"Second valid answer to this same task", "category":"qa", "source":"self-authored", "license":"CC0-1.0"},
            ])
            source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
            result = subprocess.run([sys.executable, str(ROOT / 'training' / 'prepare_dataset.py'), str(source), '--out-dir', str(root / 'split'), '--min-examples', '30'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            split = root / 'split'
            instructions = {}
            for name in ('train', 'validation', 'test'):
                entries = [json.loads(line) for line in (split / f'{name}.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
                for row in entries:
                    key = ' '.join(row['instruction'].casefold().split())
                    instructions.setdefault(key, set()).add(name)
            self.assertTrue(all(len(splits) == 1 for splits in instructions.values()), instructions)
            manifest = json.loads((split / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['instruction_split_overlap'], {'train_validation': 0, 'train_test': 0, 'validation_test': 0})

    def test_unknown_license_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'raw.jsonl'
            row = {"instruction":"Write a useful function", "response":"Return a complete valid function", "category":"py", "source":"self-authored", "license":"unknown"}
            source.write_text(json.dumps(row) + '\n', encoding='utf-8')
            valid, rejected = load_rows(source)
            self.assertEqual(valid, [])
            self.assertEqual(len(rejected), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
