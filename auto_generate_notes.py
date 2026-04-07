from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests


WORKING_DIR = Path(__file__).resolve().parent
GEMINI_INSTRUCTIONS_FILE = WORKING_DIR / "GEMINI.md"
INSTRUCTIONS_FILE = GEMINI_INSTRUCTIONS_FILE
NOTE_PROMPT_FILE = WORKING_DIR / "NOTE_PROMPT.md"
GEMINI_PATH = r"C:\Users\EddieJohnson\AppData\Roaming\npm\gemini.ps1"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3:8b"
DEFAULT_ENGINE = "gemini"
MD_DIR = WORKING_DIR / "md"
TXT_DIR = WORKING_DIR / "txt"
WAV_DIR = WORKING_DIR / "wav"
DEBUG_DIR = WORKING_DIR / "debug"
TIMESTAMP_SUFFIX_RE = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})$")
TRANSCRIPT_FILENAME_RE = re.compile(r".*\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}\.txt$")


def find_transcripts() -> list[Path]:
    return sorted(
        path
        for path in WORKING_DIR.glob("*.txt")
        if path.is_file() and TRANSCRIPT_FILENAME_RE.fullmatch(path.name)
    )


def ensure_output_dirs() -> None:
    for path in (MD_DIR, TXT_DIR, WAV_DIR, DEBUG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def display_path(path: Path) -> str:
    relative = path.relative_to(WORKING_DIR)
    return f".\\{str(relative).replace('/', '\\')}"


def markdown_output_path(transcript: Path) -> Path:
    return MD_DIR / f"{transcript.stem}.md"


def transcript_output_path(transcript: Path) -> Path:
    return TXT_DIR / transcript.name


def audio_source_path(transcript: Path) -> Path | None:
    exact_match = WORKING_DIR / f"{transcript.stem}.wav"
    if exact_match.exists():
        return exact_match

    match = TIMESTAMP_SUFFIX_RE.search(transcript.stem)
    if match is None:
        return None

    timestamp_match = WORKING_DIR / f"{match.group(1)}.wav"
    if timestamp_match.exists():
        return timestamp_match

    return None


def audio_output_path(transcript: Path) -> Path:
    return WAV_DIR / f"{transcript.stem}.wav"


def markdown_exists(transcript: Path) -> bool:
    return markdown_output_path(transcript).exists()


def read_prompt_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Failed to read {path.name}: {error}", file=sys.stderr)
        return None


def debug_output_path(transcript_stem: str, suffix: str) -> Path:
    return DEBUG_DIR / f"{transcript_stem}.{suffix}"


def write_debug_file(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        print(f"Failed to write debug file {path.name}: {error}", file=sys.stderr)


def build_user_prompt(filename: str, transcript_text: str) -> str:
    return (
        f"Transcript filename: {filename}\n\n"
        "Return only the final Markdown meeting note.\n"
        "Do not include commentary, preamble, explanations, or code fences.\n"
        "The note must begin with '# Meeting:' and follow the required meeting-note structure.\n"
        "Include these exact required headings:\n"
        "## Executive Summary\n"
        "## Decisions\n"
        "## Action Items\n"
        "## Risks / Concerns\n"
        "Do not use alternative headings such as Notes, Summary, or Key Points.\n"
        "If a required section has no content, include the heading and write '- None identified'.\n"
        "Do not invent facts.\n"
        "Do not invent participants, owners, dates, deadlines, or decisions.\n"
        "Only include people as Participants if they clearly spoke or were explicitly present in this meeting.\n"
        "People mentioned but not confirmed present must not be listed as Participants.\n"
        "If uncertain, omit or mark the uncertainty explicitly.\n"
        "Prefer omission over invention.\n\n"
        "--- TRANSCRIPT START ---\n\n"
        f"{transcript_text}\n\n"
        "--- TRANSCRIPT END ---"
    )


def extract_markdown(output: str) -> str | None:
    lines = output.splitlines(keepends=True)
    for index, line in enumerate(lines[:20]):
        if line.startswith("# Meeting:"):
            return "".join(lines[index:]).strip() + "\n"
    return None


def normalise_markdown(output: str, transcript_stem: str) -> str | None:
    cleaned_output = output.strip()
    if not cleaned_output:
        return None

    extracted_markdown = extract_markdown(cleaned_output)
    heading_detected = extracted_markdown is not None
    print(f"Markdown heading detected: {heading_detected}")
    if extracted_markdown is not None:
        write_debug_file(debug_output_path(transcript_stem, "candidate.md"), extracted_markdown)
        return extracted_markdown

    print("No markdown heading detected, falling back to raw output")
    candidate = cleaned_output + "\n"
    write_debug_file(debug_output_path(transcript_stem, "candidate.md"), candidate)
    return candidate


def validate_meeting_note(markdown: str, transcript_stem: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    required_sections = [
        "# Meeting:",
        "## Executive Summary",
        "## Decisions",
        "## Action Items",
        "## Risks / Concerns",
    ]
    for section in required_sections:
        if section not in markdown:
            reasons.append(f"Missing required section: {section}")

    top_excerpt = "\n".join(markdown.splitlines()[:12])
    disallowed_phrases = ["Here is", "Below is", "I have", "Let me know"]
    for phrase in disallowed_phrases:
        if phrase in top_excerpt:
            reasons.append(f"Contains model meta phrase near top: {phrase}")

    if "```" in markdown:
        reasons.append("Contains triple backticks")

    if reasons:
        print(f"Validation markdown length: {len(markdown)}")
        print("Validation markdown preview:")
        print(markdown[:1000])
        write_debug_file(debug_output_path(transcript_stem, "validation.txt"), "\n".join(reasons))

    return (len(reasons) == 0, reasons)


def has_only_missing_required_heading_failures(reasons: list[str]) -> bool:
    return bool(reasons) and all(reason.startswith("Missing required section: ") for reason in reasons)


def build_repair_prompt(filename: str, markdown: str) -> str:
    return (
        f"Transcript filename: {filename}\n\n"
        "Reformat the markdown below into the required meeting-note structure without adding any new facts.\n"
        "Return only markdown.\n"
        "The output must begin with '# Meeting:'.\n"
        "Include these exact required headings:\n"
        "## Executive Summary\n"
        "## Decisions\n"
        "## Action Items\n"
        "## Risks / Concerns\n"
        "Do not use alternative headings.\n"
        "If a required section has no content, include the heading and write '- None identified'.\n"
        "Do not invent facts.\n\n"
        "--- MARKDOWN TO REFORMAT START ---\n\n"
        f"{markdown}\n\n"
        "--- MARKDOWN TO REFORMAT END ---"
    )


def move_file(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination.name}")
    shutil.move(str(source), str(destination))


def generate_with_ollama(
    system_prompt: str,
    user_prompt: str,
    transcript_name: str,
    transcript_stem: str,
    raw_suffix: str = "raw.txt",
) -> str | None:
    print(f"Calling Ollama: {OLLAMA_URL} model={OLLAMA_MODEL}")
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "num_predict": 2200,
                },
            },
            timeout=300,
        )
    except requests.RequestException as error:
        print(f"Ollama request failed for {transcript_name}: {error}", file=sys.stderr)
        return None

    raw_response_text = response.text
    write_debug_file(debug_output_path(transcript_stem, raw_suffix), raw_response_text)

    if response.status_code != 200:
        detail = raw_response_text.strip() or f"HTTP {response.status_code}"
        print(f"Ollama failed for {transcript_name}: {detail}", file=sys.stderr)
        return None

    try:
        payload = response.json()
    except ValueError as error:
        print(f"Ollama returned invalid JSON for {transcript_name}: {error}", file=sys.stderr)
        return None

    print(f"Payload keys: {sorted(payload.keys())}")

    generated_text = payload.get("response")
    if not isinstance(generated_text, str) or not generated_text.strip():
        print(f"Ollama returned an empty response for {transcript_name}", file=sys.stderr)
        return None

    print(f"Response text length: {len(generated_text)}")
    print("Response preview:")
    print(generated_text[:500])

    return generated_text


def generate_with_gemini(prompt: str, transcript_name: str) -> str | None:
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
        print(f"Failed to create prompt file for {transcript_name}: {error}", file=sys.stderr)
        return None

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
        print(f"Gemini timed out after 300 seconds for {transcript_name}", file=sys.stderr)
        return None
    except OSError as error:
        print(f"Failed to start Gemini for {transcript_name}: {error}", file=sys.stderr)
        return None
    finally:
        if temp_prompt_path is not None:
            try:
                temp_prompt_path.unlink(missing_ok=True)
            except OSError as error:
                print(
                    f"Warning: failed to delete temp prompt file for {transcript_name}: {error}",
                    file=sys.stderr,
                )

    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)

    if result.returncode != 0:
        print(f"Gemini failed for {transcript_name} with exit code {result.returncode}", file=sys.stderr)
        return None

    if not result.stdout or not result.stdout.strip():
        print(f"Gemini produced no stdout for {transcript_name}", file=sys.stderr)
        return None

    return result.stdout


def generate_markdown_text(transcript: Path, engine: str) -> str | None:
    try:
        transcript_text = transcript.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Failed to read {transcript.name}: {error}", file=sys.stderr)
        return None

    print(f"Transcript filename: {transcript.name}")
    print(f"Selected engine: {engine}")
    print(f"Transcript length (chars): {len(transcript_text)}")

    if engine == "ollama":
        system_prompt = read_prompt_file(NOTE_PROMPT_FILE)
        if system_prompt is None:
            return None

        user_prompt = build_user_prompt(transcript.name, transcript_text)
        write_debug_file(debug_output_path(transcript.stem, "system.txt"), system_prompt)
        write_debug_file(debug_output_path(transcript.stem, "user.txt"), user_prompt)
        print(f"Prompt length (chars): {len(user_prompt)}")
        return generate_with_ollama(system_prompt, user_prompt, transcript.name, transcript.stem)
    if engine == "gemini":
        prompt_context = read_prompt_file(GEMINI_INSTRUCTIONS_FILE)
        if prompt_context is None:
            return None

        prompt = build_user_prompt(transcript.name, transcript_text)
        prompt = f"{prompt_context}\n\n{prompt}"
        write_debug_file(debug_output_path(transcript.stem, "prompt.txt"), prompt)
        print(f"Prompt length (chars): {len(prompt)}")
        return generate_with_gemini(prompt, transcript.name)

    print(f"Unsupported engine '{engine}' for {transcript.name}", file=sys.stderr)
    return None


def run_gemini(transcript: Path, engine: str | None = None) -> bool:
    ensure_output_dirs()

    selected_engine = (engine or os.environ.get("VIBE_NOTE_ENGINE") or DEFAULT_ENGINE).lower()
    generated_text = generate_markdown_text(transcript, selected_engine)
    if generated_text is None:
        return False

    markdown = normalise_markdown(generated_text, transcript.stem)
    if markdown is None:
        print(f"No markdown content found in {selected_engine} output for {transcript.name}", file=sys.stderr)
        return False

    is_valid, validation_reasons = validate_meeting_note(markdown, transcript.stem)
    if not is_valid and selected_engine == "ollama" and has_only_missing_required_heading_failures(validation_reasons):
        system_prompt = read_prompt_file(NOTE_PROMPT_FILE)
        if system_prompt is not None:
            repair_prompt = build_repair_prompt(transcript.name, markdown)
            write_debug_file(debug_output_path(transcript.stem, "repair.user.txt"), repair_prompt)
            repaired_text = generate_with_ollama(
                system_prompt,
                repair_prompt,
                transcript.name,
                transcript.stem,
                raw_suffix="repair.raw.txt",
            )
            if repaired_text is not None:
                markdown = normalise_markdown(repaired_text, transcript.stem)
                if markdown is None:
                    print(
                        f"No markdown content found in repaired {selected_engine} output for {transcript.name}",
                        file=sys.stderr,
                    )
                    return False
                is_valid, validation_reasons = validate_meeting_note(markdown, transcript.stem)

    if not is_valid:
        print(f"Validation failed for {transcript.name}:", file=sys.stderr)
        for reason in validation_reasons:
            print(f"- {reason}", file=sys.stderr)
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

        if audio_source is not None and audio_source.exists():
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
    if not GEMINI_INSTRUCTIONS_FILE.exists():
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
