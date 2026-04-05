#!/usr/bin/env python3
"""Report whether a .docx has headers and embedded media (logos)."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT = REPO / "templates" / "credit_note_bank_transfer.docx"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.is_file():
        raise SystemExit(f"Not found: {path}")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    headers = [n for n in names if n.startswith("word/header") and n.endswith(".xml")]
    media = [n for n in names if n.startswith("word/media/")]
    print(path)
    print(f"  header parts: {len(headers)}", headers[:5] if headers else "")
    print(f"  media files:  {len(media)}", media[:5] if media else "")
    if headers or media:
        print("  OK — has header/footer parts and/or embedded media (logos).")
    else:
        print("  Plain template — use Word export (UNI_manual_export.docx), see PROJECT.md.")


if __name__ == "__main__":
    main()
