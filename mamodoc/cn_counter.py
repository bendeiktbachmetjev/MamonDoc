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


def _compute_next_int(
    state: dict[str, Any],
    *,
    suggested_seed: str | None,
) -> int:
    stored_last = state.get("last_int")
    if stored_last is not None:
        return int(stored_last) + 1
    env_last = os.environ.get("CN_COUNTER_LAST", "").strip()
    seed = (suggested_seed or "").strip()
    parsed = _parse_trailing_int(seed) if seed else None
    if env_last.isdigit():
        return int(env_last) + 1
    if parsed is not None:
        return parsed
    return int(os.environ.get("CN_INITIAL_NEXT", "261093"))


def _format_cn_number(next_int: int) -> str:
    prefix = _prefix().strip()
    return re.sub(r"\s+", " ", f"{prefix} {next_int}".strip())


def peek_next_credit_note_number(*, suggested_seed: str | None) -> str:
    """Next credit note number without persisting (for UI preview)."""
    state = _load_state(_counter_path())
    next_int = _compute_next_int(state, suggested_seed=suggested_seed)
    return _format_cn_number(next_int)


def commit_credit_note_number(display_number: str) -> None:
    """
    After generating a document with a known number (e.g. from UI preview), advance the stored counter
    to at least that serial so the sequence does not go backwards.
    """
    parsed = _parse_trailing_int(display_number)
    if parsed is None:
        return
    path = _counter_path()
    state = _load_state(path)
    cur = state.get("last_int")
    if cur is None or parsed > int(cur):
        _atomic_write(
            path,
            {"last_int": parsed, "last_number": display_number.strip()},
        )


def allocate_next_credit_note_number(*, suggested_seed: str | None) -> str:
    """
    Return the next credit note number (e.g. 'UNI 261094') and persist last used.

    On Railway without a volume, data/ resets on redeploy — set CN_COUNTER_PATH to a mounted path for durability.
    """
    path = _counter_path()
    state = _load_state(path)
    next_int = _compute_next_int(state, suggested_seed=suggested_seed)
    number = _format_cn_number(next_int)
    _atomic_write(path, {"last_int": next_int, "last_number": number})
    return number
