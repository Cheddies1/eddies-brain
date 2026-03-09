from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


WORKING_DIR = Path(__file__).resolve().parent
INSTRUCTIONS_FILE = WORKING_DIR / "GEMINI.md"
GEMINI_PATH = r"C:\Users\EddieJohnson\AppData\Roaming\npm\gemini.ps1"
MD_DIR = WORKING_DIR / "md"
TXT_DIR = WORKING_DIR / "txt"
WAV_DIR = WORKING_DIR / "wav"


def find_transcripts() -> list[Path]:
    return sorted(path for path in WORKING_DIR.glob("*.txt") if path.is_file())


def ensure_output_dirs() -> None:
    for path in (MD_DIR, TXT_DIR, WAV_DIR):
        path.mkdir(parents=True, exist_ok=True)


def display_path(path: Path) -> str:
    relative = path.relative_to(WORKING_DIR)
    return f".\\{str(relative).replace('/', '\\')}"


def markdown_output_path(transcript: Path) -> Path:
    return MD_DIR / f"{transcript.stem}.md"


def transcript_output_path(transcript: Path) -> Path:
    return TXT_DIR / transcript.name


def audio_source_path(transcript: Path) -> Path:
    return WORKING_DIR / f"{transcript.stem}.wav"


def audio_output_path(transcript: Path) -> Path:
    return WAV_DIR / f"{transcript.stem}.wav"


def markdown_exists(transcript: Path) -> bool:
    return markdown_output_path(transcript).exists()


def build_prompt(filename: str, transcript_text: str) -> str:
    return (
        "Using the instructions in GEMINI.md in the current folder, analyse "
        f"the transcript file {filename} and generate the markdown content "
        "for a meeting note. Return only the markdown "
        "content of the note.\n\n"
        f"Transcript filename: {filename}\n\n"
        "Transcript content:\n"
        f"{transcript_text}"
    )


def extract_markdown(output: str) -> str | None:
    lines = output.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("# "):
            return "".join(lines[index:]).strip() + "\n"
    return None


def move_file(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination.name}")
    shutil.move(str(source), str(destination))


def run_gemini(transcript: Path) -> bool:
    ensure_output_dirs()

    try:
        transcript_text = transcript.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Failed to read {transcript.name}: {error}", file=sys.stderr)
        return False

    prompt = build_prompt(transcript.name, transcript_text)
    temp_prompt_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".txt",
            delete=False,
        ) as temp_file:
            temp_file.write(prompt)
            temp_prompt_path = Path(temp_file.name)
    except OSError as error:
        print(f"Failed to create prompt file for {transcript.name}: {error}", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "& { param($promptPath, $geminiPath) "
                    "$prompt = Get-Content -Path $promptPath -Raw -Encoding utf8; "
                    "$prompt | & $geminiPath --prompt '' }"
                ),
                str(temp_prompt_path),
                GEMINI_PATH,
            ],
            cwd=WORKING_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print(f"Gemini timed out after 300 seconds for {transcript.name}", file=sys.stderr)
        return False
    except OSError as error:
        print(f"Failed to start Gemini for {transcript.name}: {error}", file=sys.stderr)
        return False
    finally:
        if temp_prompt_path is not None:
            try:
                temp_prompt_path.unlink(missing_ok=True)
            except OSError as error:
                print(
                    f"Warning: failed to delete temp prompt file for {transcript.name}: {error}",
                    file=sys.stderr,
                )

    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)

    if result.returncode != 0:
        print(
            f"Gemini failed for {transcript.name} with exit code {result.returncode}",
            file=sys.stderr,
        )
        return False

    if not result.stdout or not result.stdout.strip():
        print(f"Gemini produced no stdout for {transcript.name}", file=sys.stderr)
        return False

    markdown = extract_markdown(result.stdout)
    if markdown is None:
        print(f"No markdown heading found in Gemini output for {transcript.name}", file=sys.stderr)
        return False

    output_path = markdown_output_path(transcript)
    transcript_destination = transcript_output_path(transcript)
    audio_source = audio_source_path(transcript)
    audio_destination = audio_output_path(transcript)

    try:
        output_path.write_text(markdown, encoding="utf-8")
    except OSError as error:
        print(f"Failed to write {output_path.name}: {error}", file=sys.stderr)
        return False

    transcript_moved = False
    audio_moved = False

    try:
        move_file(transcript, transcript_destination)
        transcript_moved = True

        if audio_source.exists():
            move_file(audio_source, audio_destination)
            audio_moved = True
    except OSError as error:
        print(f"Failed: {transcript.name}: {error}", file=sys.stderr)

        if audio_moved and audio_destination.exists():
            try:
                move_file(audio_destination, audio_source)
            except OSError as rollback_error:
                print(f"Rollback failed for {audio_destination.name}: {rollback_error}", file=sys.stderr)

        if transcript_moved and transcript_destination.exists():
            try:
                move_file(transcript_destination, transcript)
            except OSError as rollback_error:
                print(
                    f"Rollback failed for {transcript_destination.name}: {rollback_error}",
                    file=sys.stderr,
                )

        try:
            output_path.unlink(missing_ok=True)
        except OSError as rollback_error:
            print(f"Rollback failed for {output_path.name}: {rollback_error}", file=sys.stderr)
        return False

    print(f"Written: {display_path(output_path)}")
    print(f"Moved transcript: {display_path(transcript_destination)}")
    if audio_moved:
        print(f"Moved audio: {display_path(audio_destination)}")
    return True


def main() -> int:
    if not INSTRUCTIONS_FILE.exists():
        print("Missing required file: GEMINI.md", file=sys.stderr)
        return 1

    ensure_output_dirs()

    transcripts = find_transcripts()
    if not transcripts:
        print("No transcript files found.")
        return 0

    exit_code = 0

    for transcript in transcripts:
        if markdown_exists(transcript):
            print(f"Skipping: {transcript.name} (markdown exists)")
            continue

        print(f"Processing: {transcript.name}")
        if not run_gemini(transcript):
            print(f"Failed: {transcript.name}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
