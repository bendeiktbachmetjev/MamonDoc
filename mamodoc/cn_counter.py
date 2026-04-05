from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _counter_path() -> Path:
    raw = os.environ.get("CN_COUNTER_PATH", "").strip()
    if raw:
        return Path(raw)
    return _repo_root() / "data" / "cn_counter.json"


def _prefix() -> str:
    return os.environ.get("CN_NUMBER_PREFIX", "UNI ").strip() or "UNI "


def _parse_trailing_int(s: str) -> int | None:
    m = re.search(r"(\d+)\s*$", s.strip())
    return int(m.group(1)) if m else None


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="cn_", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def allocate_next_credit_note_number(*, suggested_seed: str | None) -> str:
    """
    Return the next credit note number (e.g. 'UNI 261094') and persist last used.
    First call: if the model suggests e.g. UNI 261093, that value is returned once; each later call is +1.

    On Railway without a volume, data/ resets on redeploy — set CN_COUNTER_PATH to a mounted path for durability.
    """
    path = _counter_path()
    state = _load_state(path)
    stored_last = state.get("last_int")

    if stored_last is not None:
        next_int = int(stored_last) + 1
    else:
        env_last = os.environ.get("CN_COUNTER_LAST", "").strip()
        seed = (suggested_seed or "").strip()
        parsed = _parse_trailing_int(seed) if seed else None
        if env_last.isdigit():
            next_int = int(env_last) + 1
        elif parsed is not None:
            next_int = parsed
        else:
            next_int = int(os.environ.get("CN_INITIAL_NEXT", "261093"))

    prefix = _prefix().strip()
    number = re.sub(r"\s+", " ", f"{prefix} {next_int}".strip())

    state = {"last_int": next_int, "last_number": number}
    _atomic_write(path, state)
    return number
