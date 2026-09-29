# Conversation, voice and storytelling improvements

User request: 26 September 2026. Continue this checklist after any interruption; do not restart the archive import or replace the existing UI.

## Intended outcome

Warm, original explanations grounded in the archive; normal greetings and identity answers; polite redirection for unrelated requests. Faster responses with measured latency. Natural multilingual speech, independent conversation-language controls, animated and narrated debate turns, narrated writings, faster translation, and a cited Ambedkar life timeline on the home page.

## Order of work

1. [implemented; live review in progress] LLM greetings/routing, connected source-grounded explanations, strict question/paragraph support checks, bounded repair and real SSE progress.
2. [implemented] Sarvam neural speech and local Piper English/Hindi narrators, stable casting, explicit synthetic narration labels and independent chat/voice/site languages. WebAudio playback and manual interruption replace the previous native playback path.
3. [implemented; latest browser review pending] Timed debate reveal with play, pause/resume, replay, speed and narration; writing read-aloud. Session context is separated; full text and original PDFs remain available.
4. [implemented] Dedicated Sarvam translation, bounded parallel requests and persistent segment/page caches. One full Hindi page took 2.895 seconds first time and 0.007 seconds cached in an earlier live check.
5. [implemented] Eight cited timeline events on the home page, with full story pages and exact local source-page links where available.
6. [in progress] 41 regression tests and the production frontend build pass. Restart API and retest live grounding/voice after stricter support checks and generation limits, inspect browser/mobile, then update README, setup and handover files.

## Findings

- The previous short-claim prompt and serial NLI/model checks were replaced with natural paragraphs and one batched support review, plus at most one repair.
- Sarvam chat, transcription, speech and dedicated translation are configured privately on this computer. Keep trial use bounded: no bulk generation, purchases or recharge. Never print or package `.env`.
- False-premise live tests exposed unrelated citations; require a positive question-support verdict and withhold claims based on missing evidence. Verify the latest fixes before declaring live acceptance.
- Synthetic speech exercises the actual voice WebSocket path. A returned audio file alone is not a passing test: its answer must also be source-checked. Physical microphone and listening quality remain untested.
- Piper runtime and individual model cards have distinct licences; some local narrator datasets are noncommercial. Do not include downloaded models in the source ZIP.
- Qwen3.5-4B already runs locally through llama.cpp. Installing Ollama alone would not make the same weights faster or constitute fine-tuning.
- No bulk cloud precomputation is enabled. Remaining trial balance is unknown.

## Resume information

Project: `C:\Users\Administrator\Desktop\DharoharAI`.
Python: read `runtime/python-path.txt`; current environment is in the original task's `work/.venv`.
App: http://127.0.0.1:8010. Model: http://127.0.0.1:8011.
Data is already imported. Preserve `.env`, originals and the live SQLite database.
No fine-tuning has been performed. Do not claim otherwise. Keep measurements and untested limitations explicit.
Latest behavior lives in `services/conversation.py`, `services/narration.py`, `services/translation.py` and `frontend/src/{Chat,Voice,ReadingExperience,Timeline}.tsx`. Live acceptance: `scripts/evaluate_improvements.py` → `docs/improvements-live-evaluation.json`.
