# Run DHAROHAR locally

## This computer

Project: `C:\Users\Administrator\Desktop\DharoharAI`.

Open PowerShell in this folder and run:

```powershell
.\scripts\Start-DHAROHAR.ps1
.\scripts\Resume-Processing.ps1
```

Open http://127.0.0.1:8010. The launcher checks existing services and avoids duplicate starts. It launches hidden background processes with logs under `data/logs`. It uses the project `.venv` if present, otherwise the machine-specific interpreter pointer in `runtime/python-path.txt`. On this development machine that pointer uses the already installed shared Python environment. Start Docker Desktop with Linux containers for OCR. Reading, chat and neural speech can run without Docker.

The local model is Qwen3.5-4B Q4_K_M through llama.cpp on loopback port 8011. This computer currently selects Sarvam for faster conversation, voice and translation; the local model remains installed. The FastAPI app binds only to 127.0.0.1:8010. Do not expose this development server publicly; it has no deployment authentication layer.

## Fresh Windows installation

Prerequisites: Python 3.12 x64, Node.js 22+ with npm, Docker Desktop with Linux containers, internet for explicit setup/import, and at least 25 GB free disk space (including download headroom). This version was exercised on Windows x64, 16 GB RAM; Raspberry Pi/ARM64 deployment is not validated.

```powershell
.\scripts\Setup-DHAROHAR.ps1 -Python 'C:\path\to\python.exe'
.\.venv\Scripts\python.exe scripts/import_archive.py
.\scripts\Start-DHAROHAR.ps1
.\scripts\Resume-Processing.ps1
```

Setup installs pinned Python dependencies, builds the React app and Debian speech/OCR image, and downloads checksum-verified model/runtime assets listed in `sources/models.json`. It preserves an existing `.env`. Neural narrator assets in `sources/neural-voices.json` add about 320 MB. Downloads total approximately 4.1 GB; archive PDF downloads are additional. `-SkipModels` and `-SkipEngine` can be used for a library-only development setup. No model is silently downloaded by a chat request.

The supplied source folder is currently `C:\Users\Administrator\Desktop\Dharohar Data`, with PDFs under `Writings and Speeches` and CSV files anywhere below it. Change `SOURCE` in `scripts/import_archive.py` for a different input folder. CSV item IDs, not filename guesses, identify debate PDFs. The importer resolves public DSpace bitstreams and verifies PDF signatures and expected byte counts. User input files remain untouched.

`python scripts/import_audio.py --download` optionally retrieves the three archival audio evaluation copies. Read `docs/AUDIO_SOURCES.md` first; the source package excludes recordings and public redistribution permission is unresolved.

## Processing and interruption

OCR and vector indexing can take hours. They write resumable page/vector records into SQLite. The full PDFs remain readable throughout. `Resume-Processing.ps1 -OcrOnly` or `-EmbeddingsOnly` runs one worker; repeat invocation checks for running workers. Indexing keeps up with new OCR text. The default OCR pass skips prior failed pages; investigate `OCR failed` rows before explicitly resetting them for retry. None of these scripts erase source files.

Process IDs and log filenames launched by the script are recorded under `runtime/processes`. To stop a service, verify its recorded PID still refers to the same command before using `Stop-Process`; PID values can be reused after a reboot. There is no scheduled task or hidden recurring automation. Close/stop the processes manually if you want to suspend background work. Run the launcher and resume script again after reboot.

## Provider selection

The supplied trial key is already in this computer's private `.env`. Do not paste keys into chat or package this file. On a fresh source copy, `.env.example` defaults to local mode. Configure these independently and restart the API after a change:

```ini
AI_PROVIDER=sarvam
VOICE_PROVIDER=sarvam
TRANSLATION_PROVIDER=sarvam
SARVAM_API_KEY=your-private-key
SARVAM_CHAT_MODEL=sarvam-105b-conversations
SARVAM_REVIEW_MODEL=sarvam-105b
TTS_ENGINE=piper
```

To return to local processing, set the three provider values to `local` and leave `TTS_ENGINE=piper`. Start the launcher to ensure the local language model is running. Local chat/translation supports the configured languages, but local neural narration currently covers English and Hindi only. Other natural speech languages need Sarvam.

Cloud mode sends relevant text/history/source excerpts or microphone audio to Sarvam. No bulk cloud work or recharge is enabled. Remaining credits are not tracked here; check the provider dashboard. If the trial expires, cloud requests can fail until the key/balance is restored or local mode is selected.

The launcher reuses a healthy server: it does **not** hot-reload `.env` or Python edits. To restart, check the PID/command for the listener on port 8010, stop only the confirmed DHAROHAR uvicorn process, then run the launcher again. Preserve the archive database and originals.

Run `python scripts/setup_neural_voices.py` to install/verify local narrators. Pinned model cards are stored in `data/models/piper`; some voice datasets are noncommercial and the runtime is GPL-3.0. Review individual terms before redistribution.

## Development and verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

For Vite development, run `npm run dev` in `frontend`; production reading uses the built `frontend/dist` served by FastAPI. On this machine `frontend/node_modules` is a junction to the first prototype's installed packages. The lockfile allows a normal fresh `npm ci`; do not recursively delete or package the junction.
