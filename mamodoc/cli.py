from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from mamodoc.defaults import DEFAULT_GEMINI_MODEL
from mamodoc.gemini_extract import resolve_cn_meta
from mamodoc.models import CreditNoteGeminiPayload
from mamodoc.pipeline import generate_bank_transfer_credit_note
from mamodoc.render_doc import render_credit_note_bank_transfer
from mamodoc.template_paths import resolve_credit_note_template


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv()
    root = _repo_root()
    default_tpl = resolve_credit_note_template(root, None)

    parser = argparse.ArgumentParser(
        description="Extract credit note fields from an invoice PDF via Gemini, render Word template.",
    )
    parser.add_argument(
        "invoice_pdf",
        type=Path,
        nargs="?",
        default=None,
        help="Path to supplier invoice PDF (optional if --from-json; used for default output name)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output .docx path (default: output/<invoice_stem>_credit_note.docx)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=default_tpl,
        help=f"docxtpl template (default: {default_tpl})",
    )
    parser.add_argument(
        "--cn-number",
        dest="cn_number",
        default=None,
        help="Override credit note number (e.g. UNI 261093)",
    )
    parser.add_argument(
        "--cn-date",
        dest="cn_date",
        default=None,
        help="Override credit note date line as printed",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_GEMINI_MODEL,
        help="Gemini model id",
    )
    parser.add_argument(
        "--dump-json",
        type=Path,
        default=None,
        help="Write extracted payload JSON to this path",
    )
    parser.add_argument(
        "--from-json",
        type=Path,
        default=None,
        help="Skip Gemini; build Word from this JSON file (for offline iteration)",
    )

    args = parser.parse_args()

    if not args.template.is_file():
        raise SystemExit(f"Template not found: {args.template}")

    if args.from_json:
        payload = CreditNoteGeminiPayload.model_validate_json(args.from_json.read_text(encoding="utf-8"))
        cn_number, cn_date = resolve_cn_meta(payload, cn_number=args.cn_number, cn_date=args.cn_date)
        ctx = payload.to_docxtpl_context(cn_number=cn_number, cn_date=cn_date)
        out = args.output
        if out is None:
            stem = args.from_json.stem
            out = root / "output" / f"{stem}_credit_note.docx"
        render_credit_note_bank_transfer(args.template, ctx, out)
    else:
        if args.invoice_pdf is None:
            raise SystemExit("invoice_pdf is required unless --from-json is set")
        if not args.invoice_pdf.is_file():
            raise SystemExit(f"Invoice PDF not found: {args.invoice_pdf}")
        docx_bytes, payload = generate_bank_transfer_credit_note(
            args.invoice_pdf,
            cn_number=args.cn_number,
            cn_date=args.cn_date,
            model_name=args.model,
            template_path=args.template,
        )
        if args.dump_json:
            args.dump_json.parent.mkdir(parents=True, exist_ok=True)
            args.dump_json.write_text(
                payload.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        out = args.output
        if out is None:
            stem = args.invoice_pdf.stem
            out = root / "output" / f"{stem}_credit_note.docx"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(docx_bytes)

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
