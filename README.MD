# Vibe Pipeline

This folder is set up as a local ingest pipeline for meeting audio, transcripts, and generated notes.

The intended flow is:

```text
root inbox
  .wav
    -> transcribe_wavs.py
  .txt
    -> watch_vibe.py
    -> auto_generate_notes.py
  .md written to .\md
  processed .txt moved to .\txt
  processed .wav moved to .\wav
```

## What Each Script Does

### `transcribe_wavs.py`

Purpose:
- scans the root working directory for `*.wav`
- uploads each WAV to the local transcription API
- writes the returned transcript text back into the root as `same-basename.txt`

Important behavior:
- only scans the root folder, not subfolders
- skips a WAV if any of these already exist:
  - `.\same-basename.txt`
  - `.\txt\same-basename.txt`
  - `.\md\same-basename.md`
- does not move the WAV
- leaves failed WAVs untouched in the root folder

API used:
- `POST http://127.0.0.1:50564/v1/audio/transcriptions`
- multipart upload with field name `file`
- expects JSON response with a `text` field

### `watch_vibe.py`

Purpose:
- watches only the root working directory for newly created `*.txt` files
- waits briefly so half-written files are not processed
- passes stable transcripts into `auto_generate_notes.run_gemini()`

Important behavior:
- does not watch subfolders
- runs continuously until interrupted with `Ctrl+C`
- creates output folders if they do not already exist:
  - `.\md`
  - `.\txt`
  - `.\wav`

### `auto_generate_notes.py`

Purpose:
- processes transcript files with Gemini CLI
- extracts markdown from Gemini stdout
- writes the note into `.\md`
- moves the processed transcript into `.\txt`
- moves a same-basename root WAV into `.\wav` if present

Important behavior:
- a transcript is considered already processed only if `.\md\same-basename.md` exists
- the root folder is treated as an inbox only
- file moves happen only after markdown is successfully written
- if processing fails, files are left in place as much as possible

Gemini behavior:
- reads `GEMINI.md` from the root folder
- reads the full transcript text into the prompt
- avoids Windows command-length issues by writing the prompt to a temporary UTF-8 file
- uses PowerShell to feed that prompt into the installed `gemini.ps1`

## Folder Layout

Expected structure under this folder:

```text
.\GEMINI.md
.\auto_generate_notes.py
.\watch_vibe.py
.\transcribe_wavs.py
.\requirements.txt
.\md\
.\txt\
.\wav\
```

Meaning of folders:
- root folder: inbox for newly created `.wav` and `.txt`
- `.\md`: generated markdown notes
- `.\txt`: processed transcript files
- `.\wav`: processed audio files

## Dependencies

Install dependencies with:

```bash
pip install -r requirements.txt
```

Current Python dependencies:
- `requests`
- `watchdog`

Environment assumptions:
- Python 3.12
- Windows
- PowerShell 7 available as `pwsh`
- Gemini CLI installed at:

```text
C:\Users\EddieJohnson\AppData\Roaming\npm\gemini.ps1
```

- local transcription API available at:

```text
http://127.0.0.1:50564
```

## Typical Usage

### One-shot transcription of root WAVs

```bash
python transcribe_wavs.py
```

This creates root `.txt` files for any unprocessed root `.wav` files.

### One-shot note generation from root TXTs

```bash
python auto_generate_notes.py
```

This generates notes into `.\md` and moves processed files into `.\txt` and `.\wav`.

### Continuous transcript watcher

```bash
python watch_vibe.py
```

This watches the root folder for new `.txt` files and processes them as they arrive.

## Recommended Operating Model

If you want the full pipeline running locally:

1. Start the transcription service and ensure it is ready.
2. Start `watch_vibe.py`.
3. Drop or create WAV files in the root folder.
4. Run `transcribe_wavs.py` on demand, or later automate that separately.
5. The generated root `.txt` files will be picked up by the watcher.
6. Notes will be written to `.\md`, and processed source files moved into `.\txt` and `.\wav`.

## Logging Conventions

The scripts currently log simple status messages such as:
- `Processing: filename.wav`
- `Wrote transcript: filename.txt`
- `Watching folder...`
- `New transcript detected: filename.txt`
- `Written: .\md\filename.md`
- `Moved transcript: .\txt\filename.txt`
- `Moved audio: .\wav\filename.wav`
- `Skipping: ...`
- `Failed: ...`

## Known Constraints

- `watch_vibe.py` only reacts to newly created root `.txt` files; it does not back-process old files automatically.
- `transcribe_wavs.py` is one-shot, not a watcher.
- `auto_generate_notes.py` depends on Gemini CLI behavior staying compatible with the current prompt-based invocation.
- The transcription API is assumed to return JSON with a non-empty `text` field.
- Historical files already in the root are not automatically reorganized unless they are actively processed by the scripts.

## Key Files

- [auto_generate_notes.py](c:/Users/EddieJohnson/Documents/Vibe/auto_generate_notes.py)
- [watch_vibe.py](c:/Users/EddieJohnson/Documents/Vibe/watch_vibe.py)
- [transcribe_wavs.py](c:/Users/EddieJohnson/Documents/Vibe/transcribe_wavs.py)
- [GEMINI.md](c:/Users/EddieJohnson/Documents/Vibe/GEMINI.md)
- [requirements.txt](c:/Users/EddieJohnson/Documents/Vibe/requirements.txt)
