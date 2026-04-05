from __future__ import annotations

import os
from pathlib import Path


def resolve_credit_note_template(root: Path, override: Path | None = None) -> Path:
    """
    Template resolution order:
    1) explicit override path
    2) env CREDIT_NOTE_TEMPLATE_PATH (absolute or relative to cwd)
    3) templates/template new.docx if present (simplified letterhead template)
    4) templates/credit_note_bank_transfer.docx
    """
    if override is not None:
        return override
    env = os.environ.get("CREDIT_NOTE_TEMPLATE_PATH", "").strip()
    if env:
        p = Path(env)
        if not p.is_file():
            p = root / env
        if p.is_file():
            return p
    simplified = root / "templates" / "template new.docx"
    if simplified.is_file():
        return simplified
    return root / "templates" / "credit_note_bank_transfer.docx"
