# Audio collection provenance

Three files were retrieved on 25 September 2026 from Internet Archive Wayback snapshots of the official Dr. Ambedkar Foundation audio gallery. TLS validation remained enabled. The original government host could not be fetched with valid TLS from this computer, so its archived public files were used.

These are local research and evaluation copies. They have **not** been cleared for public redistribution and must be excluded from public source packages and deployments.

## Recordings

| ID | Recording | Duration | Type |
| --- | --- | --- | --- |
| `audio-assembly-1946-12-17-excerpt` | Constituent Assembly speech — 17 December 1946 (excerpt) | 1m 23s | Historical speech excerpt |
| `audio-volume-1-introduction` | Writings & Speeches, Volume 1 — introduction | 58s | Modern narration; not Ambedkar's voice |
| `audio-volume-1-part-ii` | Writings & Speeches, Volume 1 — Part II | 61m 11s | Modern narration; not Ambedkar's voice |

The [official gallery](https://drambedkarwritings.gov.in/content/audiogallery.php) dates the first excerpt to 17 December 1946. Its opening discusses the difficulty of beginning a common political undertaking and bringing different parties and sections together. The same speech's date and Prasar Bharati provenance are independently identified by the [Constitution of India museum](https://www.constitutionofindia.net/museum/1946-b-r-ambedkar-on-the-muslim-leagues-absence-from-the-constituent-assembly/).

The introduction lists the contents of Volume 1. The file called Part II in the gallery starts with Chapter 1, *Castes in India: Their Mechanism, Genesis and Development*. The source's Part II filename is preserved as a label; it must not be confused with the second part of a speech spoken by Ambedkar. The narrator is not credited in the gallery. The gallery's Part I link leads to an archived error page and has not been imported.

## Validation and catalogue treatment

All three files were decoded using PyAV and have audio streams. Their durations, exact byte sizes, SHA-256 checksums, original URLs, archive capture times and download URLs are recorded in `sources/audio.json`. The opening 35 seconds of each file were checked using local Whisper; those transcripts remain unreviewed research material and are **not indexed as RAG evidence**. The full recordings have not received a manual listening review.

Summaries are labelled **Curated source overview**. The two narrations are explicitly described as modern readings. Source MP4 containers are retained unchanged; the speech excerpt also contains video, while the introduction has only an audio stream. The app can play their audio locally alongside the MP3.

## Source conditions

The archived official [copyright policy](https://web.archive.org/web/20220609045224id_/http://drambedkarwritings.gov.in/content/page/website-policies.php) requires department permission for reproduction and acknowledgement when referring to its content. The Foundation's [2026 policy snapshot](https://web.archive.org/web/20260117232048id_/https://ambedkarfoundation.nic.in/Websitepolicies.html) likewise calls for permission, accurate reproduction, prominent source credit and separate clearance for third-party material. No open redistribution licence was found. Download availability alone is not recorded as an open licence.

The files under `data/originals/` and the research copies under `work/audio-candidates/` must remain outside public source archives. Preserve this provenance and seek the relevant permission before publishing recordings to others. This importer does not send messages or request permissions on the user's behalf.

## Reimport

Run `python scripts/import_audio.py` from the project root to import the existing verified local copies. The operation is idempotent and updates only the three audio document IDs and their English overviews in one SQLite transaction. It never modifies PDF records, pages, speaker turns or retrieval chunks.

On a fresh local evaluation installation, `python scripts/import_audio.py --download` retrieves missing files from the exact HTTPS archival URLs and verifies size, checksum, duration and the presence of an audio stream before insertion. Original recordings are not bundled with the source project.

## Playback compatibility

The original MP4 files remain preserved. The importer also produces mono 128 kbps MP3 playback copies for their audio streams and serves those copies to avoid relying on video codecs. The long source MP3 plays unchanged. Original download checksums remain in the source manifest; catalogue checksums identify the served playback copy. PyAV decoded both source and derived audio. The Codex embedded preview renderer crashed when Play was clicked for both AAC and MP3; audible playback in a regular Chrome/Edge browser still needs confirmation on this machine.
