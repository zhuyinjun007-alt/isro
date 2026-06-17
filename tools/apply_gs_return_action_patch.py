from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROUND = "phase-isro-new-return-actions-20260617"
REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "evidence" / "2026-06-17-phase-isro-new-return-actions-manifest.json"
BACKUP_ROOT = Path.home() / "Documents" / "添加ISRO的返回功能" / "backups"
CSRO_GS = Path(r"D:\CSRO\8-SR_GameServer.exe")
REFSKILV = b"_REFSKILV"


class PatchBlocked(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def file_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if path.exists():
        stat = path.stat()
        info.update(
            {
                "sha256": sha256_file(path),
                "length": stat.st_size,
                "last_write_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            }
        )
    return info


def hex_bytes(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def parse_int(value: Any, field: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError as exc:
            raise PatchBlocked(f"invalid integer for {field}: {value}") from exc
    raise PatchBlocked(f"missing or invalid integer for {field}")


def parse_hex_bytes(value: Any, field: str) -> bytes:
    if not isinstance(value, str):
        raise PatchBlocked(f"missing or invalid hex bytes for {field}")
    compact = value.replace(" ", "").replace("-", "").replace("_", "")
    if len(compact) % 2:
        raise PatchBlocked(f"odd-length hex bytes for {field}: {value}")
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise PatchBlocked(f"invalid hex bytes for {field}: {value}") from exc


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PatchBlocked(f"missing JSON file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise PatchBlocked(f"invalid JSON file: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PatchBlocked(f"JSON root must be an object: {path}")
    return payload


def normalize_path(value: str) -> str:
    return str(Path(value)).casefold()


def find_manifest_file(manifest: dict[str, Any], target: Path) -> dict[str, Any]:
    target_norm = normalize_path(str(target))
    for entry in manifest.get("live_files", []):
        if isinstance(entry, dict) and normalize_path(str(entry.get("path", ""))) == target_norm:
            return entry
    raise PatchBlocked(f"manifest does not contain live target entry: {target}")


def find_manifest_backup(manifest: dict[str, Any], target_name: str) -> dict[str, Any]:
    for entry in manifest.get("backup", {}).get("files", []):
        if isinstance(entry, dict) and Path(str(entry.get("path", ""))).name.casefold() == target_name.casefold():
            return entry
    raise PatchBlocked(f"manifest does not contain backup entry for {target_name}")


def check_manifest_and_backup(round_name: str, target: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    manifest = load_json(MANIFEST_PATH)
    checks["manifest"] = {"path": str(MANIFEST_PATH), "round": manifest.get("round")}
    if manifest.get("round") != round_name:
        raise PatchBlocked(f"manifest round mismatch: expected {round_name}, actual {manifest.get('round')}")

    live_entry = find_manifest_file(manifest, target)
    if not target.exists():
        raise PatchBlocked(f"target GS does not exist: {target}")
    actual_hash = sha256_file(target)
    expected_hash = str(live_entry.get("sha256", "")).upper()
    checks["target_hash"] = {"expected": expected_hash, "actual": actual_hash}
    if actual_hash != expected_hash:
        raise PatchBlocked(f"target hash mismatch: expected {expected_hash}, actual {actual_hash}")

    backup_entry = find_manifest_backup(manifest, "8-SR_GameServer.exe")
    backup_dir = BACKUP_ROOT / round_name
    backup_path = backup_dir / "8-SR_GameServer.exe"
    checks["backup"] = {"path": str(backup_path), "exists": backup_path.exists()}
    if not backup_path.exists():
        raise PatchBlocked(f"missing round backup GS: {backup_path}")
    backup_hash = sha256_file(backup_path)
    expected_backup_hash = str(backup_entry.get("sha256", "")).upper()
    checks["backup_hash"] = {"expected": expected_backup_hash, "actual": backup_hash}
    if backup_hash != expected_backup_hash:
        raise PatchBlocked(f"backup hash mismatch: expected {expected_backup_hash}, actual {backup_hash}")

    if backup_hash != actual_hash:
        raise PatchBlocked("backup hash does not match current target hash; refusing to patch an unfrozen state")

    return checks


def load_patch_spec(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise PatchBlocked(
            "missing reviewed patch spec; GS reverse evidence is insufficient for binary write"
        )
    spec = load_json(path)
    if spec.get("round") != ROUND:
        raise PatchBlocked(f"patch spec round mismatch: expected {ROUND}, actual {spec.get('round')}")
    target = Path(str(spec.get("target", "")))
    if normalize_path(str(target)) != normalize_path(str(CSRO_GS)):
        raise PatchBlocked(f"patch spec target must be {CSRO_GS}, actual {target}")
    if spec.get("review_status") != "approved_for_write":
        raise PatchBlocked("patch spec review_status must be approved_for_write")
    patches = spec.get("patches")
    if not isinstance(patches, list) or not patches:
        raise PatchBlocked("patch spec must contain a non-empty patches list")
    return spec


def validate_and_simulate(spec: dict[str, Any], target: Path) -> tuple[bytes, list[dict[str, Any]]]:
    original = target.read_bytes()
    data = bytearray(original)
    applied: list[dict[str, Any]] = []

    pre_hash = str(spec.get("pre_sha256", "")).upper()
    actual_hash = sha256_file(target)
    if pre_hash and pre_hash != actual_hash:
        raise PatchBlocked(f"patch spec pre_sha256 mismatch: expected {pre_hash}, actual {actual_hash}")

    if REFSKILV not in original:
        raise PatchBlocked("_REFSKILV is not present before patch; refusing because preservation boundary is unclear")

    for index, patch in enumerate(spec["patches"]):
        if not isinstance(patch, dict):
            raise PatchBlocked(f"patch #{index} must be an object")
        raw = parse_int(patch.get("raw_offset"), f"patches[{index}].raw_offset")
        old = parse_hex_bytes(patch.get("old_bytes"), f"patches[{index}].old_bytes")
        new = parse_hex_bytes(patch.get("new_bytes"), f"patches[{index}].new_bytes")
        if len(old) != len(new):
            raise PatchBlocked(f"patch #{index} old/new byte lengths differ")
        if raw < 0 or raw + len(old) > len(data):
            raise PatchBlocked(f"patch #{index} raw range is outside target")
        actual_old = bytes(data[raw : raw + len(old)])
        if actual_old != old:
            raise PatchBlocked(
                f"patch #{index} old bytes mismatch at 0x{raw:X}: "
                f"expected {hex_bytes(old)}, actual {hex_bytes(actual_old)}"
            )
        evidence = patch.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise PatchBlocked(f"patch #{index} must include evidence references")
        reason = str(patch.get("reason", "")).strip()
        if not reason:
            raise PatchBlocked(f"patch #{index} must include a reason")

        data[raw : raw + len(old)] = new
        applied.append(
            {
                "index": index,
                "raw_offset": f"0x{raw:X}",
                "old_bytes": hex_bytes(old),
                "new_bytes": hex_bytes(new),
                "reason": reason,
                "evidence": evidence,
            }
        )

    simulated = bytes(data)
    if REFSKILV not in simulated:
        raise PatchBlocked("patch simulation removes _REFSKILV; refusing to write")
    return simulated, applied


def build_blocked_payload(reason: str, checks: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "round": ROUND,
        "tool": Path(__file__).name,
        "status": "blocked",
        "reason": reason,
        "mode": "safe_default_no_write",
        "target": file_info(CSRO_GS),
        "checks": checks or {},
    }


def print_payload(payload: dict[str, Any], json_mode: bool) -> None:
    if json_mode:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        sys.stdout.buffer.write(text.encode("utf-8"))
        return
    print(f"{payload['tool']}: {payload['status']}")
    print(f"reason: {payload.get('reason', '-')}")
    for name, value in payload.get("checks", {}).items():
        print(f"{name}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Safely apply a reviewed CSRO GS return-action patch. "
            "Without an approved patch spec this exits non-zero and writes nothing."
        )
    )
    parser.add_argument("--round", default=ROUND, help="round name")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument("--spec", type=Path, help="approved patch spec JSON")
    parser.add_argument("--execute", action="store_true", help="write the validated patch to live GS")
    args = parser.parse_args()

    checks: dict[str, Any] = {}
    try:
        if args.round != ROUND:
            raise PatchBlocked(f"unsupported round: {args.round}")
        checks.update(check_manifest_and_backup(args.round, CSRO_GS))
        spec = load_patch_spec(args.spec)
        simulated, applied = validate_and_simulate(spec, CSRO_GS)
        payload: dict[str, Any] = {
            "round": ROUND,
            "tool": Path(__file__).name,
            "status": "dry_run_validated",
            "mode": "no_write",
            "target": file_info(CSRO_GS),
            "checks": checks,
            "patches": applied,
            "post_sha256_if_applied": hashlib.sha256(simulated).hexdigest().upper(),
            "refskilv_preserved_if_applied": REFSKILV in simulated,
        }
        if args.execute:
            CSRO_GS.write_bytes(simulated)
            payload["status"] = "patched"
            payload["mode"] = "wrote_live_gs"
            payload["target_after"] = file_info(CSRO_GS)
        print_payload(payload, args.json)
        return 0
    except PatchBlocked as exc:
        payload = build_blocked_payload(str(exc), checks)
        print_payload(payload, args.json)
        return 2


if __name__ == "__main__":
    sys.exit(main())
