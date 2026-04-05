from __future__ import annotations

import base64
import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi import Query
from fastapi.responses import JSONResponse, Response

from mamodoc.pipeline import generate_bank_transfer_credit_note

load_dotenv()

app = FastAPI(title="MamoDoc", version="0.1.0")


def _safe_filename(name: str) -> str:
    base = os.path.basename(name or "invoice")
    base = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE)
    return base[:180] if len(base) > 180 else base or "invoice"


def _verify_bearer(authorization: str | None) -> None:
    expected = os.environ.get("MAMODOC_API_KEY", "").strip()
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/credit-note/bank-transfer")
async def credit_note_bank_transfer(
    request: Request,
    file: UploadFile = File(..., description="Supplier invoice PDF"),
    cn_number: str | None = Form(None),
    cn_date: str | None = Form(None),
    model: str | None = Form(None),
    include_json: bool = Query(False, description="If true, return JSON with base64 docx + payload"),
) -> Response:
    _verify_bearer(request.headers.get("Authorization"))

    body = await file.read()
    if not body:
        raise HTTPException(status_code=400, detail="Empty file")

    model_name = (model or os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash").strip()

    try:
        docx_bytes, payload = generate_bank_transfer_credit_note(
            body,
            cn_number=cn_number,
            cn_date=cn_date,
            model_name=model_name,
        )
    except RuntimeError as e:
        if "GEMINI_API_KEY" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Server misconfiguration: GEMINI_API_KEY is not set",
            ) from e
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}") from e

    stem = _safe_filename(file.filename or "invoice").removesuffix(".pdf") or "invoice"
    out_name = f"{stem}_credit_note.docx"

    if include_json:
        return JSONResponse(
            {
                "filename": out_name,
                "payload": payload.model_dump(),
                "docx_base64": base64.b64encode(docx_bytes).decode("ascii"),
            }
        )

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )
