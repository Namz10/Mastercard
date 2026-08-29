"""Human-in-the-loop (HITL) rule approval, rejection, and rollback queue (Phase 5 / Ticket 7)."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

import yaml

from packages.eval.fit import _recipe_hash
from packages.policy.rules import DEFAULT_RULES_PATH, load_v0_rules, parse_predicate

_RULES_DIR = Path(__file__).resolve().parents[2] / "data" / "rules"
DEFAULT_DRAFTS_PATH = _RULES_DIR / "drafts.json"
DEFAULT_VERSIONS_PATH = _RULES_DIR / "versions.json"
DEFAULT_BACKUPS_DIR = _RULES_DIR / "backups"
DEFAULT_AUDIT_PATH = _RULES_DIR / "audit.log"


def load_drafts(path: Path | str | None = None) -> list[dict[str, Any]]:
    p = Path(path) if path else DEFAULT_DRAFTS_PATH
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_drafts(drafts: list[dict[str, Any]], path: Path | str | None = None) -> None:
    p = Path(path) if path else DEFAULT_DRAFTS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(drafts, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, p)


def get_versions(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_VERSIONS_PATH
    if not p.is_file():
        return {"current_version": 1, "history": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"current_version": 1, "history": []}


def save_versions(versions: dict[str, Any], path: Path | str | None = None) -> None:
    p = Path(path) if path else DEFAULT_VERSIONS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(versions, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, p)


def log_audit(
    action: str,
    draft_id: str,
    resulting_version: int,
    note: str = "",
    *,
    audit_path: Path | str | None = None,
    actor: str = "hitl_demo",
) -> None:
    p = Path(audit_path) if audit_path else DEFAULT_AUDIT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": pd_ts_now(),
        "action": action,
        "draft_id": draft_id,
        "resulting_version": resulting_version,
        "actor": actor,
        "note": note,
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def pd_ts_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def approve_draft(
    draft_id: str,
    *,
    rules_path: Path | str | None = None,
    drafts_path: Path | str | None = None,
    versions_path: Path | str | None = None,
    backups_dir: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    r_path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
    d_path = Path(drafts_path) if drafts_path else DEFAULT_DRAFTS_PATH
    v_path = Path(versions_path) if versions_path else DEFAULT_VERSIONS_PATH
    b_dir = Path(backups_dir) if backups_dir else DEFAULT_BACKUPS_DIR
    b_dir.mkdir(parents=True, exist_ok=True)

    drafts = load_drafts(d_path)
    target = None
    target_idx = -1
    for i, d in enumerate(drafts):
        if d.get("id") == draft_id:
            target = d
            target_idx = i
            break

    if target is None:
        raise KeyError(f"draft_id not found: {draft_id}")

    # Optimistic concurrency check: must be reviewable — "proposed" (human- or
    # orchestrator-triggered) or "auto_rejected" (LLM judgement a human may override).
    # approve() re-runs parse_predicate on every clause below regardless of origin.
    if target.get("status") not in ("proposed", "auto_rejected"):
        raise ValueError(f"draft {draft_id} cannot be approved from status {target.get('status')!r}")

    # Re-mine invalidation check: verify recipe_hash matches current recipe
    current_hash = _recipe_hash()
    draft_hash = target.get("recipe_hash", "")
    if draft_hash and draft_hash != current_hash:
        raise ValueError(
            f"Recipe hash mismatch (draft={draft_hash[:16]}... current={current_hash[:16]}...). Draft is stale — please re-mine."
        )

    # Re-parse every predicate clause
    when_exprs = target.get("when") or []
    for expr in when_exprs:
        parse_predicate(str(expr))

    # Versioning & backup
    versions = get_versions(v_path)
    cur_v = versions.get("current_version", 1)

    # Backup current rules file
    backup_file = b_dir / f"v0_rules.v{cur_v}.yaml"
    if r_path.is_file():
        shutil.copy2(r_path, backup_file)
    else:
        backup_file.write_text("[]\n", encoding="utf-8")

    # Read existing raw rules list
    raw_rules = []
    if r_path.is_file():
        loaded_raw = yaml.safe_load(r_path.read_text(encoding="utf-8"))
        if isinstance(loaded_raw, list):
            raw_rules = loaded_raw

    # Build new rule entry
    new_rule_entry = {
        "id": target["id"],
        "kind": target.get("kind", "hard_flag"),
        "applies_to": target["applies_to"],
        "when": list(when_exprs),
        "reason": target.get("reason", f"Loop T mined rule for {target['applies_to']}"),
        "status": "live",
    }
    if target.get("min_score") is not None:
        new_rule_entry["min_score"] = target["min_score"]
    if target.get("technique_ids"):
        new_rule_entry["technique_ids"] = list(target["technique_ids"])

    raw_rules.append(new_rule_entry)

    # Write updated rules atomically (Must stay list-root, NO _meta key!)
    tmp_rules = r_path.with_suffix(".tmp")
    tmp_rules.write_text(yaml.safe_dump(raw_rules, sort_keys=False), encoding="utf-8")
    os.replace(tmp_rules, r_path)

    # Verify updated rules YAML is valid list-root
    verify_rules = load_v0_rules(r_path)
    assert isinstance(verify_rules, list), "Rules YAML must remain a list"

    # Bump version
    next_v = cur_v + 1
    versions["current_version"] = next_v
    versions.setdefault("history", []).append({
        "version": cur_v,
        "action": "approve",
        "draft_id": draft_id,
        "backup": str(backup_file.name),
        "timestamp": pd_ts_now(),
    })
    save_versions(versions, v_path)

    # Mark draft approved
    target["status"] = "approved"
    target["approved_at"] = pd_ts_now()
    save_drafts(drafts, d_path)

    log_audit("approve", draft_id, next_v, note=f"Approved rule {draft_id}", audit_path=audit_path)

    return target


def reject_draft(
    draft_id: str,
    note: str = "",
    *,
    drafts_path: Path | str | None = None,
    versions_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    d_path = Path(drafts_path) if drafts_path else DEFAULT_DRAFTS_PATH
    v_path = Path(versions_path) if versions_path else DEFAULT_VERSIONS_PATH

    drafts = load_drafts(d_path)
    target = None
    for d in drafts:
        if d.get("id") == draft_id:
            target = d
            break

    if target is None:
        raise KeyError(f"draft_id not found: {draft_id}")

    if target.get("status") != "proposed":
        raise ValueError(f"draft {draft_id} cannot be rejected from status {target.get('status')!r}")

    target["status"] = "rejected"
    target["rejection_note"] = note
    target["rejected_at"] = pd_ts_now()
    save_drafts(drafts, d_path)

    cur_v = get_versions(v_path).get("current_version", 1)
    log_audit("reject", draft_id, cur_v, note=note or "Rejected by HITL", audit_path=audit_path)

    return target


def rollback_rules(
    target_version: int,
    *,
    rules_path: Path | str | None = None,
    versions_path: Path | str | None = None,
    backups_dir: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    r_path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
    v_path = Path(versions_path) if versions_path else DEFAULT_VERSIONS_PATH
    b_dir = Path(backups_dir) if backups_dir else DEFAULT_BACKUPS_DIR

    backup_file = b_dir / f"v0_rules.v{target_version}.yaml"
    if not backup_file.is_file():
        raise FileNotFoundError(f"No backup file found for version {target_version} at {backup_file}")

    # Backup integrity check: verify it parses as a valid rule list
    try:
        parsed_rules = load_v0_rules(backup_file)
        assert isinstance(parsed_rules, list), "Backup must parse as a list of rules"
    except Exception as exc:
        raise ValueError(f"Backup file for version {target_version} is corrupted: {exc}") from exc

    # Atomic copy backup to live rules path
    tmp_rules = r_path.with_suffix(".tmp")
    shutil.copy2(backup_file, tmp_rules)
    os.replace(tmp_rules, r_path)

    # Update versions
    versions = get_versions(v_path)
    versions["current_version"] = target_version
    versions.setdefault("history", []).append({
        "version": target_version,
        "action": "rollback",
        "timestamp": pd_ts_now(),
    })
    save_versions(versions, v_path)

    log_audit("rollback", "N/A", target_version, note=f"Rolled back to v{target_version}", audit_path=audit_path)

    return {"status": "rolled_back", "version": target_version}
