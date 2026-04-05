from __future__ import annotations

from pathlib import Path

from docxtpl import DocxTemplate


def render_credit_note_bank_transfer(
    template_path: Path,
    context: dict,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    tpl.save(str(output_path))
    return output_path
