import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'benchmarks' / 'run_interactivity.py'
SPEC = importlib.util.spec_from_file_location('interactivity', PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class InteractivityProtocol(unittest.TestCase):
    def test_visible_clock_and_gap_crossing_use_absolute_ns(self):
        lines = [
            (1_000_000_000, 'data: {"choices":[{"delta":{"role":"assistant","content":""},"finish_reason":null}]}'),
            (2_000_000_000, 'data: {"choices":[{"delta":{"content":"a"},"finish_reason":null}]}'),
            (5_500_000_000, 'data: {"choices":[{"delta":{"content":"b"},"finish_reason":"stop"}]}'),
            (5_600_000_000, 'data: {"choices":[],"usage":{"prompt_tokens":9,"completion_tokens":2}}'),
            (5_700_000_000, 'data: [DONE]'),
        ]
        parsed = MOD.parse_sse(lines)
        self.assertEqual(parsed['visible_event_ns'], [2_000_000_000, 5_500_000_000])
        self.assertEqual(MOD.gaps(parsed['visible_event_ns']), [3.5])
        self.assertEqual(MOD.crossing_gap(parsed['visible_event_ns'], 3_000_000_000, 5_000_000_000), 3.5)
        self.assertIsNone(MOD.crossing_gap(parsed['visible_event_ns'], 5_600_000_000, 6_000_000_000))

    def test_usage_done_and_poisoned_incomplete_stream(self):
        good = [(1, 'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}'),
                (2, 'data: {"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1}}'), (3, 'data: [DONE]')]
        parsed = MOD.parse_sse(good)
        self.assertTrue(parsed['done'])
        self.assertEqual(parsed['usage']['prompt_tokens'], 1)
        poisoned = MOD.parse_sse(good[:-1])
        self.assertFalse(poisoned['done'])

    def test_sanitize_removes_message_bodies(self):
        self.assertEqual(MOD.sanitize({'messages': [{'content': 'private'}], 'base_url': 'http://127.0.0.1:8000', 'output_dir': '/home/private', 'timing': 3}), {'timing': 3})


if __name__ == '__main__':
    unittest.main()
