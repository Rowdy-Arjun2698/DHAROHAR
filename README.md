# DHAROHAR AI

An Ambedkar archive built around **Discover → Overview → Read or Listen → Ask**.
**Deployed Project** https://dharohar-seven.vercel.app/
**Open:** http://127.0.0.1:8010  
**This computer:** `C:\Users\Administrator\Desktop\DharoharAI`  
**Start:** `Start-DHAROHAR.cmd` or `scripts\Start-DHAROHAR.ps1`.

## Current experience — 26 September 2026

- Scroll through Debates, Writings & Speeches and Audio. Read an overview, then open the full text or original PDF inside the app. Each collection has search and original-language filters.
- Ask DHAROHAR for explanations in its own words, with source-page links and expandable exact quotations. Greetings and identity questions use the LLM without archive retrieval; unrelated requests invite an Ambedkar question. Unsupported questions can be declined.
- Chat language and spoken conversation language are independent of the website language. English, Hindi, Marathi, Gujarati, Bengali, Tamil, Telugu, Kannada, Malayalam and Punjabi are selectable. Navigation localization remains partial (English/Hindi/Marathi); new timeline/control copy is currently English.
- Voice uses neural narration, three narrator styles, automatic listening after playback, repeat and manual interruption. WebAudio replaces the previous native playback path for generated speech.
- In a debate reader, choose **Watch the debate**. Reveal passages every 2, 2.5, 3 or 5 seconds, pause, resume, replay or advance manually. Enable Narration to hear passages sequentially. Known speakers get stable voice casting; unknown speakers use a neutral narrator profile. Long turns are divided for reading; stage directions are separate.
- **Read aloud** works for writings and translated pages. All new narration is explicitly synthetic, not Ambedkar's original voice or an authentic recreation. The finite voice pool can repeat across speakers.
- Translation uses a dedicated service, sentence-aware segments, up to three concurrent requests and persistent caches. Original speaker labels remain intact; known gender hints are passed for debate translation.
- The home page has eight events in Ambedkar's life, with short introductions, full detail pages and citations to local PDF pages or primary institutional sources.

## Models, privacy and trial usage

This computer currently uses **Sarvam** for chat, speech and translation, following the user's supplied trial key. Chat uses `sarvam-105b-conversations`, with a separate `sarvam-105b` support review. Cloud requests send the question, recent conversation and relevant archive excerpts; speech sends the recorded utterance. The private key stays in `.env`, excluded from packages and source control.

There is no bulk cloud generation, purchase or automatic recharge. Greeting, translation and narration caches reduce repeat calls. Remaining provider credits are **not measured** by this app. A configured key is not proof of available credit; failures produce a retryable message.

Local mode remains available: Qwen3.5-4B through llama.cpp, multilingual MiniLM/FTS5 retrieval, Whisper small transcription and Piper neural English/Hindi voices. Local CPU inference is slower. See [setup and provider switching](docs/SETUP.md). ChatGPT Plus/Go is not an API credential for embedding ChatGPT Voice; OpenAI API usage requires separate API access/billing ([OpenAI pricing](https://learn.chatgpt.com/docs/pricing)).

## Archive and processing

The corrected input folder contributed **505 debates resolved from six CSVs**, **20 writing PDFs**, and **46,472 PDF pages**. Three audio records are also present: one historical excerpt and two modern narrated readings. All debate downloads/imports completed with zero reported errors. Original user files were preserved. See `docs/import-report.json`, `docs/corrected-input-audit.json` and [audio provenance](docs/AUDIO_SOURCES.md).

The latest snapshot has **120,694 searchable and embedded passages**. OCR and embedding worker jobs report complete; OCR text remains unreviewed, and covers/poor scans can still need attention. `/api/status` and the footer show live state. Re-run `scripts\Resume-Processing.ps1` after adding or correcting source material; completed processing is resumable.

## Evidence from this build

- **43 automated tests pass**. TypeScript and the production frontend build pass.
- The seven-case live set passed greetings, identity, off-topic redirection, English/Hindi explanations and false-premise abstention. Exact citation quotations matched the stored pages. Greetings took **0.26–0.28 seconds**; the two cited answers took **1.64–3.64 seconds** in this run. These are observed samples, not latency guarantees or a correctness benchmark.
- A synthetic spoken question completed real Sarvam transcription → grounded answer → valid neural WAV over WebSocket in **5.84 seconds**. This is not a physical microphone or listening-quality test.
- An earlier uncached Hindi page translation took **2.90 seconds**; latest cache hits took **0.03–0.04 seconds**. Translation quality is not certified across ten languages.
- Browser checks covered separate language selectors, sequential debate reveal, narration pause/resume/stop and a 390-pixel layout. Generated playback did not reproduce the prior embedded native-player crash. Existing archival audio controls still need real-browser listening verification.

Reproduce the bounded live set with `python scripts/evaluate_improvements.py`; it uses configured provider credits. Results are in `docs/improvements-live-evaluation.json`. Previous `chat-evaluation`, `voice-evaluation` and diagnostic files record older experiments, including failures; they are not the final acceptance report.

## Limits and next review

RAG supplies evidence; a model synthesizes and another model reviews support. Code validates source IDs, checks a verdict for each paragraph and refuses malformed/incomplete reviews. Source relevance, missing-evidence claims and false premises have regression coverage. These measures reduce hallucinations but **do not eliminate them**. A model reviewer can still err; open the original for important claims.

No model has been fine-tuned. There is no reviewed training set or held-out historical accuracy benchmark yet. See [AI evaluation](docs/AI_EVALUATION.md). Some questions may over-abstain. Summaries are on-demand reading guides from sampled contents/pages, not exhaustive summaries of every volume. Writings remain grouped by volume, not a fully curated essay catalogue.

Voice is turn-based with manual interruption, not full-duplex GPT Live equivalence. Cancelling discards late UI results; a provider call already running can finish. Real microphones, accents, echo handling and all language/voice combinations need user testing. Machine translation may mishandle legal terms, gender in unlabelled prose or OCR errors.

Piper's runtime is GPL-3.0; voice datasets have separate terms. Ryan and the installed Hindi models declare CC-BY-NC-SA 4.0, while LJSpeech declares public domain and Alan refers to its upstream terms. Model cards are saved next to downloaded voices. Review rights before commercial redistribution; weights and archive recordings are excluded from the source package.

This is a loopback-only Windows development app without public-service authentication. Raspberry Pi/ARM64 performance and storage targets are not validated.

## Code map

| Location | Responsibility |
| --- | --- |
| `frontend/src/{Chat,Voice,ReadingExperience,Timeline}.tsx` | Conversation, speech, animated reader and history views |
| `app/main.py` | Catalogue, reader, translation, SSE chat, WebSocket voice and story endpoints |
| `app/retrieval.py`, `services/conversation.py` | Hybrid retrieval, routing, generation, support checks and citations |
| `services/{voice,narration,translation}.py` | Provider adapters, synthetic casting and cached translation |
| `ingestion`, `scripts` | Resumable extraction, OCR, setup, launch and evaluation |
| `sources` | Pinned download manifests, provenance and cited timeline |
| `data`, `runtime` | Private local originals, models, caches and processes; excluded from packages |

## Build log


1. **25 September:** planned a new visitor-first project after feedback about complexity. Preserved the previous prototype separately.
2. **25 September:** re-audited the corrected source folder. Parsed 505 unique CSV links, resolved official bitstreams and imported 20 corrected writing PDFs plus all 505 debates.
3. **25 September:** built the three-section interface, overview flow, local reader and audio player; began resumable OCR and multilingual vector indexing.
4. **25–26 September:** tested Qwen3.5-2B and found over-abstention and unreliable structured output. Switched this desktop build to Qwen3.5-4B, bounded generation and added evidence validation, independent contradiction screening and reasoned review. Rejected unsupported drafts rather than showing them.
5. **25–26 September:** fixed constituency-colon parsing, false office/prose speakers, officer directories and unnamed interjections. Rebuilt stored speaker turns. Fixed stale translation/summary responses and voice session cleanup.
6. **25–26 September:** added three provenance-labelled audio items; retained originals and made MP3 playback derivatives for the two MP4s. Verified local transcription and speech generation, then the complete voice WebSocket path.
7. **26 September:** added reproducible pinned setup, hidden-process launch/resume scripts, checksummed model manifest, Docker engine recipe, regression tests, mobile inspection and this status/limitations record. OCR and indexing continue in the background.

8. **26 September:** replaced the short-claim chat flow with natural explanations, social routing, batched support review, bounded repair and real progress stages. Enabled the user-authorized Sarvam trial privately; retained local inference.
9. **26 September:** installed pinned Piper narrators; added Sarvam neural voices, stable synthetic casting, independent conversation languages, WebAudio playback and stale-event cancellation.
10. **26 September:** added timed/narrated debate passages and writing read-aloud, dedicated cached translation, and eight cited home-page stories.
11. **26 September:** live evaluation exposed false-premise citations, mismatched review paragraphs and a constrained-output whitespace loop. Fixed source relevance, ID-mapped review checks, source limits and output schema; verified the final live set. Added regression coverage and refreshed the source-only handover.
