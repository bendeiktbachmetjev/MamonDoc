#!/usr/bin/env python3
"""
Build docxtpl-enabled credit note template from Company/UNI 2026.03.21.doc (macOS textutil).
Run from repo root: python scripts/patch_credit_note_template.py

For logos / exact corporate graphics: open the .doc in Microsoft Word, Save As .docx into
templates/UNI_2026.03.21.docx, then run this script (or rely on textutil if your doc has no images).
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC_SRC = REPO / "Company" / "UNI 2026.03.21.doc"
SRC = REPO / "templates" / "UNI_2026.03.21.docx"
OUT = REPO / "templates" / "credit_note_bank_transfer.docx"


def main() -> None:
    if DOC_SRC.is_file() and platform.system() == "Darwin":
        SRC.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [
                "textutil",
                "-convert",
                "docx",
                "-output",
                str(SRC),
                str(DOC_SRC),
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print("textutil failed:", r.stderr or r.stdout, file=sys.stderr)
            sys.exit(1)
        print(f"Converted {DOC_SRC.name} -> {SRC.relative_to(REPO)}")
    elif not SRC.is_file():
        raise SystemExit(
            f"Missing {SRC}. On macOS place {DOC_SRC.name} in Company/ and run again, "
            "or copy a .docx export from Word as templates/UNI_2026.03.21.docx."
        )

    tmp = REPO / "templates" / "_patch_credit_note"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    with zipfile.ZipFile(SRC, "r") as zin:
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


if __name__ == "__main__":
    main()
