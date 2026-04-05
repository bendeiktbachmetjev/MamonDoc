from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from docxtpl import DocxTemplate

logger = logging.getLogger(__name__)


def _template_looks_plain(docx: Path) -> bool:
    try:
        with zipfile.ZipFile(docx) as z:
            names = z.namelist()
    except OSError:
        return False
    has_header = any(n.startswith("word/header") and n.endswith(".xml") for n in names)
    has_media = any(n.startswith("word/media/") for n in names)
    # Letterhead usually adds header/footer parts and/or images in word/media/
    return not (has_header or has_media)


def render_credit_note_bank_transfer(
    template_path: Path,
    context: dict,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if _template_looks_plain(template_path):
        logger.warning(
            "Credit note template has no header/media (plain layout). "
            "Export Company/UNI 2026.03.21.doc from Word to templates/UNI_manual_export.docx "
            "and run scripts/patch_credit_note_template.py — see PROJECT.md."
        )
    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    tpl.save(str(output_path))
    return output_path
