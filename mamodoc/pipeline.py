from __future__ import annotations

import tempfile
from pathlib import Path
from typing import BinaryIO

from mamodoc.gemini_extract import extract_from_invoice_pdf, resolve_cn_meta
from mamodoc.models import CreditNoteGeminiPayload
from mamodoc.render_doc import render_credit_note_bank_transfer


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def generate_bank_transfer_credit_note(
    invoice_pdf: Path | bytes | BinaryIO,
    *,
    cn_number: str | None = None,
    cn_date: str | None = None,
    model_name: str = "gemini-2.0-flash",
    template_path: Path | None = None,
) -> tuple[bytes, CreditNoteGeminiPayload]:
    """
    Run Gemini on the invoice PDF and render the bank-transfer credit note template.
    Returns (.docx bytes, extraction payload).
    """
    root = _repo_root()
    tpl = template_path or (root / "templates" / "credit_note_bank_transfer.docx")
    if not tpl.is_file():
        raise FileNotFoundError(f"Template not found: {tpl}")

    cleanup: Path | None = None
    if isinstance(invoice_pdf, Path):
        pdf_path = invoice_pdf
    else:
        data = invoice_pdf.read() if hasattr(invoice_pdf, "read") else invoice_pdf
        if not isinstance(data, bytes):
            raise TypeError("invoice_pdf must be Path, bytes, or a binary stream")
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(data)
        tmp.close()
        pdf_path = Path(tmp.name)
        cleanup = pdf_path

    try:
        payload = extract_from_invoice_pdf(pdf_path, model_name=model_name)
        cn_num, cn_dt = resolve_cn_meta(payload, cn_number=cn_number, cn_date=cn_date)
        ctx = payload.to_docxtpl_context(cn_number=cn_num, cn_date=cn_dt)
        out_tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        out_tmp.close()
        out_path = Path(out_tmp.name)
        try:
            render_credit_note_bank_transfer(tpl, ctx, out_path)
            docx_bytes = out_path.read_bytes()
        finally:
            out_path.unlink(missing_ok=True)
        return docx_bytes, payload
    finally:
        if cleanup is not None:
            cleanup.unlink(missing_ok=True)
