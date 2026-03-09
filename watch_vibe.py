from __future__ import annotations

import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from auto_generate_notes import (
    INSTRUCTIONS_FILE,
    WORKING_DIR,
    ensure_output_dirs,
    markdown_exists,
    run_gemini,
)


SETTLE_SECONDS = 2.0
STABLE_POLLS = 3
POLL_INTERVAL = 1.0


def wait_for_stable_file(path: Path) -> bool:
    stable_checks = 0
    last_size: int | None = None

    time.sleep(SETTLE_SECONDS)

    for _ in range(STABLE_POLLS * 4):
        if not path.exists():
            return False

        try:
            current_size = path.stat().st_size
        except OSError:
            return False

        if current_size > 0 and current_size == last_size:
            stable_checks += 1
            if stable_checks >= STABLE_POLLS:
                return True
        else:
            stable_checks = 0
            last_size = current_size

        time.sleep(POLL_INTERVAL)

    return False


class TranscriptHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        self.processing: set[Path] = set()

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        transcript = Path(event.src_path)
        if transcript.suffix.lower() != ".txt":
            return
        if transcript.parent != WORKING_DIR:
            return
        if transcript in self.processing:
            return

        self.processing.add(transcript)
        try:
            print(f"New transcript detected: {transcript.name}")

            if not wait_for_stable_file(transcript):
                print(f"Failed: {transcript.name}", file=sys.stderr)
                return

            if markdown_exists(transcript):
                print(f"Skipping: {transcript.name} (markdown exists)")
                return

            if not run_gemini(transcript):
                print(f"Failed: {transcript.name}", file=sys.stderr)
        finally:
            self.processing.discard(transcript)


def main() -> int:
    if not INSTRUCTIONS_FILE.exists():
        print("Missing required file: GEMINI.md", file=sys.stderr)
        return 1

    ensure_output_dirs()

    event_handler = TranscriptHandler()
    observer = Observer()
    observer.schedule(event_handler, str(WORKING_DIR), recursive=False)
    observer.start()

    print(f"Watching folder... {WORKING_DIR}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.join()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
