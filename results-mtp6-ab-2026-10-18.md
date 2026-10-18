# MTP3 vs MTP6 first pilot — 2026-10-18 (superseded)

This historical one-wave pilot is retained for audit, but its comparison is
**unqualified** and must not be used as a repeated performance result. The
harness generated a different leading nonce for every request but hashed only
the prompt suffix, so cold/warm and MTP3/MTP6 payloads were not exact replays.
It also had one repetition per family, stored no raw grounding response, and
its raw SSE files were overwritten when the second profile ran. Consequently,
its earlier warm labels, percentages and grounding failure boolean cannot
establish matched performance or a model-quality failure.

The first pilot did physically run MTP6 without a recorded safety fault and
then restored MTP3. It is historical evidence of that limited operational fact
only. The corrected three-repetition measurement and current decision are in
[the repaired MTP3/MTP6 A/B report](results-mtp6-ab-repair-2026-10-18.md).
