#!/usr/bin/env python3
"""
Inject docxtpl placeholders into the UNI credit note body.

Source .docx priority (best first):
  1) templates/UNI_manual_export.docx — export from Microsoft Word (keeps logos, headers, borders, media).
  2) LibreOffice headless conversion from Company/UNI 2026.03.21.doc (often keeps images better than textutil).
  3) macOS textutil (usually STRIPS images — last resort).
  4) Existing templates/UNI_2026.03.21.docx

Output: templates/credit_note_bank_transfer.docx

Run from repo root: python scripts/patch_credit_note_template.py
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC_SRC = REPO / "Company" / "UNI 2026.03.21.doc"
MANUAL_DOCX = REPO / "templates" / "UNI_manual_export.docx"
SRC = REPO / "templates" / "UNI_2026.03.21.docx"
OUT = REPO / "templates" / "credit_note_bank_transfer.docx"


def _soffice_candidates() -> list[str]:
    return [
        "soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
    ]


def _convert_via_libreoffice(doc_path: Path, dest_docx: Path) -> bool:
    if not doc_path.is_file():
        return False
    tmpd = tempfile.mkdtemp(prefix="lo_docx_")
    try:
        for cmd in _soffice_candidates():
            try:
                r = subprocess.run(
                    [cmd, "--headless", "--convert-to", "docx", "-outdir", tmpd, str(doc_path)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
            if r.returncode != 0:
                continue
            produced = Path(tmpd) / f"{doc_path.stem}.docx"
            if produced.is_file():
                dest_docx.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(produced, dest_docx)
                print(f"LibreOffice converted -> {dest_docx.relative_to(REPO)}")
                return True
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    return False


def _convert_via_textutil(doc_path: Path, dest_docx: Path) -> bool:
    if platform.system() != "Darwin" or not doc_path.is_file():
        return False
    dest_docx.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["textutil", "-convert", "docx", "-output", str(dest_docx), str(doc_path)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print("textutil failed:", r.stderr or r.stdout, file=sys.stderr)
        return False
    print(f"textutil converted -> {dest_docx.relative_to(REPO)} (images often missing)")
    return True


def resolve_source_docx() -> Path:
    if MANUAL_DOCX.is_file():
        print(
            f"Using {MANUAL_DOCX.relative_to(REPO)} (Word export — letterhead and images preserved)."
        )
        return MANUAL_DOCX

    if _convert_via_libreoffice(DOC_SRC, SRC):
        return SRC

    if _convert_via_textutil(DOC_SRC, SRC):
        return SRC

    if SRC.is_file():
        print(
            f"Using existing {SRC.relative_to(REPO)}. If output has no logo, add "
            f"{MANUAL_DOCX.name} (Word Save As .docx) — see PROJECT.md."
        )
        return SRC

    raise SystemExit(
        f"No source .docx. Either:\n"
        f"  - Save As: Company/UNI 2026.03.21.doc -> {MANUAL_DOCX}\n"
        f"  - Or install LibreOffice and keep {DOC_SRC.name} in Company/\n"
        f"  - Or on macOS keep the .doc in Company/ for textutil (no images)."
    )


def main() -> None:
    src_path = resolve_source_docx()

    tmp = REPO / "templates" / "_patch_credit_note"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    with zipfile.ZipFile(src_path, "r") as zin:
        zin.extractall(tmp)

    doc_xml = (tmp / "word" / "document.xml").read_text(encoding="utf-8")

    def replace_first(hay: str, old: str, new: str) -> str:
        i = hay.find(old)
        if i == -1:
            raise SystemExit(f"Patch failed, substring not found: {old[:80]}...")
        return hay[:i] + new + hay[i + len(old) :]

    replacements: list[tuple[str, str]] = [
        (
            ">CREDIT NOTE No. UNI 2026/03/21</w:t>",
            ">CREDIT NOTE No. {{ cn_number }}</w:t>",
        ),
        (">March  30.  2026</w:t>", ">{{ cn_date }}</w:t>"),
        (
            ">        V SHIPS FRANCE SAS</w:t>",
            ">{{ payer_company }}</w:t>",
        ),
        (
            ">Herewith we confirm that the company „Unimars“ (Klaipėda, Lithuania) has supplied m/v  </w:t>",
            ">Herewith we confirm that the company „{{ supplier_name }}“ ({{ supplier_city }}, {{ supplier_country }}) has supplied m/v  </w:t>",
        ),
        (">„ECO LEVANT“  </w:t>", ">„{{ vessel_name }}“  </w:t>"),
        (">UNI 2603/22/B of March 30</w:t>", ">{{ inv1_id_before_comma }}</w:t>"),
        (">          615,00 EUR</w:t>", ">{{ inv1_gross }}</w:t>"),
        (">Deducting 9.76% discount - </w:t>", ">Deducting {{ inv1_discount_pct }}% discount - </w:t>"),
        (">                         - 60,00 EUR</w:t>", ">                         - {{ inv1_discount_eur }}</w:t>"),
        (">555,00 EUR</w:t>", ">{{ inv1_net }}</w:t>"),
        (">UNI 2603/68 of March 30</w:t>", ">{{ inv2_id_before_comma }}</w:t>"),
        (">          695,10 EUR</w:t>", ">{{ inv2_gross }}</w:t>"),
        (">Deducting 5.965% discount - </w:t>", ">Deducting {{ inv2_discount_pct }}% discount - </w:t>"),
        (">                         - 41,46 EUR</w:t>", ">                         - {{ inv2_discount_eur }}</w:t>"),
        (">653,64 EUR</w:t>", ">{{ inv2_net }}</w:t>"),
        (">1208,64 EUR</w:t>", ">{{ total_ship }}</w:t>"),
        (">   UAB “Unimars” </w:t>", ">   {{ signer_company }} </w:t>"),
        (">               Manager Ina Selest</w:t>", ">               Manager {{ signer_name }}</w:t>"),
        (">              Bankas „SWEDBANK“ AB </w:t>", ">              {{ bank_name }} </w:t>"),
        (
            ">    Konstitucijos pr. 20A, Vilnius, Lithuania</w:t>",
            ">    {{ bank_address }}</w:t>",
        ),
        (">    S.W.I.F.T. :HABALT LT22</w:t>", ">    {{ bank_swift }}</w:t>"),
        (">    Account N..:LT40 7300 0100 9417 8770</w:t>", ">    {{ bank_account }}</w:t>"),
    ]

    for old, new in replacements:
        doc_xml = replace_first(doc_xml, old, new)

    doc_xml = replace_first(doc_xml, ">, 2026  </w:t>", ">{{ inv1_comma_year }}</w:t>")
    doc_xml = replace_first(doc_xml, ">, 2026  </w:t>", ">{{ inv2_comma_year }}</w:t>")

    inv2_open = (
        "<w:p><w:pPr></w:pPr>"
        '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
        '<w:sz w:val="24"/><w:sz-cs w:val="24"/></w:rPr>'
        "<w:t>{%p if has_second_invoice %}</w:t></w:r></w:p>"
    )
    inv2_close = (
        "<w:p><w:pPr></w:pPr>"
        '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
        '<w:sz w:val="24"/><w:sz-cs w:val="24"/></w:rPr>'
        "<w:t>{%p endif %}</w:t></w:r></w:p>"
    )

    needle = ">{{ inv2_id_before_comma }}</w:t>"
    idx = doc_xml.find(needle)
    if idx == -1:
        raise SystemExit("Cannot locate inv2 anchor for conditional wrap")
    p_start = doc_xml.rfind("<w:p>", 0, idx)
    if p_start == -1:
        raise SystemExit("Cannot find paragraph start for inv2")
    doc_xml = doc_xml[:p_start] + inv2_open + doc_xml[p_start:]

    needle_net = ">{{ inv2_net }}</w:t>"
    idx_net = doc_xml.find(needle_net)
    if idx_net == -1:
        raise SystemExit("Cannot locate inv2 net anchor")
    p_end = doc_xml.find("</w:p>", idx_net)
    if p_end == -1:
        raise SystemExit("Cannot find paragraph end after inv2 net")
    p_end += len("</w:p>")
    doc_xml = doc_xml[:p_end] + inv2_close + doc_xml[p_end:]

    (tmp / "word" / "document.xml").write_text(doc_xml, encoding="utf-8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        for path in sorted(tmp.rglob("*")):
            if path.is_file():
                arc = path.relative_to(tmp).as_posix()
                zout.write(path, arc)

    shutil.rmtree(tmp)
    print(f"Wrote {OUT}")
    _print_letterhead_hint(OUT)


def _print_letterhead_hint(docx: Path) -> None:
    with zipfile.ZipFile(docx) as z:
        names = z.namelist()
    has_header = any(n.startswith("word/header") and n.endswith(".xml") for n in names)
    has_media = any(n.startswith("word/media/") for n in names)
    if not has_header and not has_media:
        print(
            "\nWARNING: No word/header* and no word/media — output will look plain (typical for textutil).\n"
            f"  Fix: export from Word to {MANUAL_DOCX.relative_to(REPO)} and re-run this script.\n"
            f"  Check: python scripts/check_template_letterhead.py\n"
        )


if __name__ == "__main__":
    main()
