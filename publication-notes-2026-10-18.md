# Publication notes — 2026-10-18

This repository is published with explicit owner approval. Making it public does not certify a clean-host reproduction, upstream licensing, general model quality, or a performance win over TensorFold.

## What was checked before publication

- All eight existing commits and 82 unique historical blobs were scanned, plus current text files, using local checks for credentials, authorization headers, private home paths and private/Tailnet addresses. No findings remained under these checks. This was a pattern-based audit, not a claim of exhaustive secret detection; `gitleaks` was not installed.
- The only bundled image is the synthetic OCR fixture. No model weights, external chat template, real client photos, private deployment configuration or credential files are distributed.
- Seven CPU-only tests passed, including execution of the multimodal producer's actual pure hash/grading helpers and rejection of swapped/incorrect/incomplete fixtures. The publication did not invoke inference or change the serving model.
- JSON/JSONL parsing and local Markdown links were checked. Local tests are not a claim of GitHub Actions CI status.
- The TensorFold media/prefix-reuse statement and its implementation were fetched from the public recipe at commit `06df57f8a76c74fec908c87fdbc4dd702ff598f9`. That was also the recipe's current HEAD when checked. The README links to the exact lines, not an invented issue or a universal TensorFold limitation.
- The corrected multimodal results preserve original capture grades and distinguish offline regrading from new inference. Lack of media/encoder metrics remains inconclusive. MTP6 is still not run and paused.

## Attribution and boundaries

The explanatory material is provided in Spanish and English. IA para Filmmakers links identify the author's independent practical mentoring/advisory work. They do not imply endorsement by TensorFold, vLLM, NVIDIA or the upstream recipe authors, and technical results are not a guarantee of client outcomes.

Upstream models, images, patches and templates retain their own licensing. This publication does not redistribute the required model export or template and does not grant a new license to third-party material. See [provenance.md](provenance.md) and the README's input requirements before attempting reproduction.

Raw deployment-specific evidence stays local. Public reports contain sanitized timing, usage, hashes and scoped conclusions. Later measurements should be added as dated results; unexecuted experiments must remain explicitly unrun.
