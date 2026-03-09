from __future__ import annotations

import sys
from pathlib import Path

import requests


WORKING_DIR = Path(__file__).resolve().parent
API_URL = "http://127.0.0.1:50564/v1/audio/transcriptions"
TIMEOUT_SECONDS = 600
TXT_DIR = WORKING_DIR / "txt"
MD_DIR = WORKING_DIR / "md"


def find_wavs() -> list[Path]:
    return sorted(path for path in WORKING_DIR.glob("*.wav") if path.is_file())


def transcript_exists(wav_path: Path) -> bool:
    root_txt = WORKING_DIR / f"{wav_path.stem}.txt"
    processed_txt = TXT_DIR / f"{wav_path.stem}.txt"
    markdown = MD_DIR / f"{wav_path.stem}.md"
    return root_txt.exists() or processed_txt.exists() or markdown.exists()


def transcribe_wav(wav_path: Path) -> bool:
    print(f"Processing: {wav_path.name}")

    try:
        with wav_path.open("rb") as audio_file:
            response = requests.post(
                API_URL,
                files={"file": (wav_path.name, audio_file, "audio/wav")},
                timeout=TIMEOUT_SECONDS,
            )
    except requests.RequestException as error:
        print(f"Failed: {wav_path.name}: {error}", file=sys.stderr)
        return False
    except OSError as error:
        print(f"Failed: {wav_path.name}: {error}", file=sys.stderr)
        return False

    if response.status_code != 200:
        detail = response.text.strip() or f"HTTP {response.status_code}"
        print(f"Failed: {wav_path.name}: {detail}", file=sys.stderr)
        return False

    try:
        payload = response.json()
    except ValueError as error:
        print(f"Failed: {wav_path.name}: invalid JSON response: {error}", file=sys.stderr)
        return False

    transcript_text = payload.get("text")
    if not isinstance(transcript_text, str) or not transcript_text.strip():
        print(f"Failed: {wav_path.name}: response did not contain non-empty text", file=sys.stderr)
        return False

    transcript_path = WORKING_DIR / f"{wav_path.stem}.txt"

    try:
        transcript_path.write_text(transcript_text, encoding="utf-8")
    except OSError as error:
        print(f"Failed: {wav_path.name}: {error}", file=sys.stderr)
        return False

    print(f"Wrote transcript: {transcript_path.name}")
    return True


def main() -> int:
    wavs = find_wavs()
    if not wavs:
        print("No wav files found.")
        return 0

    exit_code = 0

    for wav_path in wavs:
        if transcript_exists(wav_path):
            print(f"Skipping: {wav_path.name} (transcript or markdown already exists)")
            continue

        if not transcribe_wav(wav_path):
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
