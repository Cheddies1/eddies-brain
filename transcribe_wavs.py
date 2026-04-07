from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests


WORKING_DIR = Path(__file__).resolve().parent
DEFAULT_API_BASE_URLS = (
    "http://127.0.0.1:56478",
    "http://127.0.0.1:50564",
)
TIMEOUT_SECONDS = 600
TXT_DIR = WORKING_DIR / "txt"
MD_DIR = WORKING_DIR / "md"
DEFAULT_MODEL_PATH = (
    Path(r"C:\Users\EddieJohnson\AppData\Local\github.com.thewh1teagle.vibe")
    / "ggml-large-v3-turbo.bin"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", type=int)
    parser.add_argument("-p", "--port", dest="port_flag", type=int)
    return parser.parse_args()


def build_api_urls(port: int | None = None) -> list[str]:
    candidates: list[str] = []

    if port is not None:
        return [f"http://127.0.0.1:{port}/v1/audio/transcriptions"]

    env_values = (
        os.environ.get("SONA_API_URL"),
        os.environ.get("SONA_BASE_URL"),
    )

    for value in env_values:
        if not value:
            continue
        normalized = value.rstrip("/")
        if normalized.endswith("/v1/audio/transcriptions"):
            candidates.append(normalized)
        else:
            candidates.append(f"{normalized}/v1/audio/transcriptions")

    for base_url in DEFAULT_API_BASE_URLS:
        candidates.append(f"{base_url}/v1/audio/transcriptions")

    deduped: list[str] = []
    for url in candidates:
        if url not in deduped:
            deduped.append(url)

    return deduped


def find_wavs() -> list[Path]:
    return sorted(path for path in WORKING_DIR.glob("*.wav") if path.is_file())


def transcript_exists(wav_path: Path) -> bool:
    root_txt = WORKING_DIR / f"{wav_path.stem}.txt"
    processed_txt = TXT_DIR / f"{wav_path.stem}.txt"
    markdown = MD_DIR / f"{wav_path.stem}.md"
    return root_txt.exists() or processed_txt.exists() or markdown.exists()


def extract_base_url(api_url: str) -> str:
    return api_url.rsplit("/v1/audio/transcriptions", 1)[0]


def load_model(base_url: str) -> bool:
    if not DEFAULT_MODEL_PATH.exists():
        print(f"Failed: model file not found: {DEFAULT_MODEL_PATH}", file=sys.stderr)
        return False

    load_url = f"{base_url}/v1/models/load"
    print(f"Loading model: {DEFAULT_MODEL_PATH.name}")

    try:
        response = requests.post(
            load_url,
            json={"path": str(DEFAULT_MODEL_PATH)},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        print(f"Failed: model load request failed: {error}", file=sys.stderr)
        return False

    if response.status_code != 200:
        detail = response.text.strip() or f"HTTP {response.status_code}"
        print(f"Failed: model load failed: {detail}", file=sys.stderr)
        return False

    return True


def transcribe_request(api_url: str, wav_path: Path) -> requests.Response:
    with wav_path.open("rb") as audio_file:
        return requests.post(
            api_url,
            files={"file": (wav_path.name, audio_file, "audio/wav")},
            timeout=TIMEOUT_SECONDS,
        )


def transcribe_wav(wav_path: Path, port: int | None = None) -> bool:
    print(f"Processing: {wav_path.name}")

    response = None
    last_error: Exception | None = None
    last_api_url: str | None = None

    try:
        for api_url in build_api_urls(port):
            try:
                response = transcribe_request(api_url, wav_path)
                last_api_url = api_url
                print(f"Using transcription API: {api_url}")
                break
            except requests.RequestException as error:
                last_error = error
    except OSError as error:
        print(f"Failed: {wav_path.name}: {error}", file=sys.stderr)
        return False

    if response is None:
        detail = last_error or "no transcription API endpoints available"
        print(f"Failed: {wav_path.name}: {detail}", file=sys.stderr)
        return False

    if response.status_code != 200:
        if last_api_url is not None:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = None

            if (
                isinstance(error_payload, dict)
                and isinstance(error_payload.get("error"), dict)
                and error_payload["error"].get("code") == "no_model"
            ):
                base_url = extract_base_url(last_api_url)
                if load_model(base_url):
                    try:
                        response = transcribe_request(last_api_url, wav_path)
                    except (requests.RequestException, OSError) as error:
                        print(f"Failed: {wav_path.name}: {error}", file=sys.stderr)
                        return False

        detail = response.text.strip() or f"HTTP {response.status_code}"
        if response.status_code != 200:
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
    args = parse_args()
    selected_port = args.port_flag if args.port_flag is not None else args.port

    wavs = find_wavs()
    if not wavs:
        print("No wav files found.")
        return 0

    exit_code = 0

    for wav_path in wavs:
        if transcript_exists(wav_path):
            print(f"Skipping: {wav_path.name} (transcript or markdown already exists)")
            continue

        if not transcribe_wav(wav_path, selected_port):
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
