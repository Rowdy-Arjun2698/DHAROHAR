# AI checks and remaining work

Current default on this computer: Sarvam conversation model plus a separate support-review model. Local Qwen3.5-4B remains available. Retrieval uses multilingual MiniLM vectors and SQLite FTS5 reciprocal-rank fusion. The former NLI/per-claim chat path has been replaced; legacy summary helpers remain separate.

## Current checks

1. Route greetings and identity questions to a short LLM response; politely redirect unrelated requests.
2. Retrieve four archive passages, preserving original PDF page links.
3. Generate connected explanatory paragraphs with explicit evidence IDs. No external historical knowledge is allowed to fill gaps.
4. Review question relevance and all assertions against assigned passages in one batch. Match checks by paragraph ID, require complete valid coverage, and reject unsupported paragraphs. One bounded repair is allowed.
5. Assign displayed citations in code and copy normalized source quotes exactly. Missing support, incomplete output or provider failure never falls back to an unchecked draft.

Real SSE stages expose progress; only the checked final answer is sent. These are fallible safeguards, not a correctness guarantee. A source quote's existence is not proof that an interpretation follows from it. Broad questions and poor OCR can still produce over-abstention or misleading explanations.

## Verification — 26 September 2026

43 automated tests passed; production TypeScript/Vite build passed. The final seven-case report `improvements-live-evaluation.json` passed expected chat statuses and exact quote matching. It includes social turns, unrelated requests, English/Hindi concept answers and a fabricated internet-invention premise. Observed grounded chat: 1.64–3.64 s. Voice: 5.84 s from a synthetic English WAV through actual STT, source-checked answer and neural WAV delivery. All 12 local timeline citation links returned readable source pages.

The final report supersedes older experimental JSON files. Earlier failures exposed irrelevant citations, review IDs that did not correspond to paragraphs and whitespace output loops from tight schema string limits. The current workflow addresses those specific regressions. Live model results are not deterministic.

Run `python -m pytest -q` for isolated tests. `python scripts/evaluate_improvements.py` is a bounded live integration set and **uses configured provider credits**. Do not run bulk benchmarks against a small trial. It uses synthetic audio, not the physical microphone. Browser checks verified progressive debate reveal, WebAudio controls, separate language selectors and a phone-width layout. Actual audibility, naturalness, accents/noise and ten-language accuracy remain unreviewed.

Before public release, curate at least 100 reviewed questions across concepts, dates, contested attribution, false premises, source gaps and follow-ups. Hold out complete documents/sessions to avoid chunk leakage. Score factual correctness, citation precision, refusal appropriateness, translation fidelity, OCR quality and latency separately. Test consented microphone recordings with varied accents and noise; keep retention minimal.

## Fine-tuning boundary

No weights were trained. Raw PDFs are evidence, not a reviewed instruction dataset. A later LoRA stage needs curated question/source/reviewed-answer/refusal examples, provenance, document-level held-out splits and suitable hardware. Compare any adapter with the unchanged baseline before deployment, and retain RAG/citation checks. Training on the current CPU machine and deployment to Raspberry Pi are not validated.

## Translation and narration

Dedicated Sarvam translation works per segment with bounded parallelism and persistent caches. Speaker labels stay unchanged, and known debate-speaker gender is passed explicitly. Unlabelled prose, legal wording and OCR errors still require checking against the original. No reviewed ten-language quality claim is made.

Sarvam neural narration is currently active. Piper English/Hindi models are installed for local mode, with saved model cards. Synthetic casting is a reading aid, not historical voice cloning. Voice sessions are turn-based, with automatic listening after playback and manual interruption; they are not full-duplex GPT Live. Already-running provider calls may finish after UI cancellation.

## Provider documentation

- [Sarvam chat API](https://docs.sarvam.ai/api-reference/chat/chat-completions-v1)
- [Sarvam translation and speaker-gender hints](https://docs.sarvam.ai/api-reference/text/translate-text)
- [Sarvam neural speech](https://docs.sarvam.ai/api-reference/text-to-speech/convert)
- [Piper Python API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)
