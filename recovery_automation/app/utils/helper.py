"""
Shared helpers for backup metadata, IDs, and safe path handling.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.config import MODULE_ROOT, get_settings
from app.utils.logger import get_logger

logger = get_logger("helper")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_backup_id() -> str:
    return f"bk_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def metadata_path(backup_id: str) -> Path:
    return get_settings().backup_root_path / f"{backup_id}.meta.json"


def archive_path(backup_id: str) -> Path:
    return get_settings().backup_root_path / f"{backup_id}.zip"


def write_metadata(backup_id: str, data: dict[str, Any]) -> Path:
    path = metadata_path(backup_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def read_metadata(backup_id: str) -> dict[str, Any] | None:
    path = metadata_path(backup_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_path_string(raw: str) -> str:
    """
    Strip whitespace and wrapping quotes copied from dialogs or URLs.

    Paths wrapped in straight or curly quotation marks fail pathlib.exists()
    until stripped (common when copying paths from dialogs or chats).
    fail pathlib.exists() unless we strip those characters.
    """
    p = raw.strip().strip("\ufeff")
    quote_pairs = (
        ('"', '"'),
        ("'", "'"),
        ("\u201c", "\u201d"),
        ("\u2018", "\u2019"),
    )
    changed = True
    while changed and len(p) >= 2:
        changed = False
        for left, right in quote_pairs:
            if p.startswith(left) and p.endswith(right):
                p = p[len(left) : -len(right)].strip()
                changed = True
                break
    return p.strip()


def resolve_safe_paths(paths: list[str]) -> list[Path]:
    """
    Resolve user-supplied paths relative to module root; reject path traversal.
    """
    base = MODULE_ROOT.resolve()
    resolved: list[Path] = []
    for raw in paths:
        normalized = normalize_path_string(raw if isinstance(raw, str) else str(raw))
        if not normalized:
            continue
        candidate = Path(normalized)
        if not candidate.is_absolute():
            candidate = (MODULE_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            # Allow paths outside module root only if they exist (explicit user choice)
            logger.warning("Path outside module root allowed: %s", candidate)
        if candidate.exists():
            resolved.append(candidate)
        else:
            logger.warning("Skipping missing path: %s", candidate)
    return resolved


def prune_old_backups(retention_days: int) -> int:
    """Remove backup archives older than retention_days. Returns count removed."""
    from datetime import timedelta

    root = get_settings().backup_root_path
    if not root.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for meta in root.glob("*.meta.json"):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            created = datetime.fromisoformat(data.get("created_at", ""))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created < cutoff:
                backup_id = data.get("backup_id", meta.stem.replace(".meta", ""))
                zip_file = archive_path(backup_id)
                meta.unlink(missing_ok=True)
                zip_file.unlink(missing_ok=True)
                removed += 1
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.error("Failed to prune %s: %s", meta, exc)
    return removed
