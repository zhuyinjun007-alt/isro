# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


DEFAULT_TARGET = Path(r"F:\CSRO客户端\SRO_Client.exe")
DEFAULT_MANIFEST = Path(r"evidence\2026-06-17-phase-isro-new-return-actions-manifest.json")
DEFAULT_ROUND = "phase-isro-new-return-actions-20260617"
EXPECTED_APPLIED_HASH = "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E"
EXPECTED_PRE_PHASE2_HASH = "BE9D5D0D62CC931F71B80ACEC88FBB2F297B78BF6C712A57D4A80E286615119C"
RAW_GATE = 0x00C6F9C0
RAW_CHECKSUM = 0x180
OLD_GATE_BYTES = bytes.fromhex("83 79 30 02 0F 9D C0 C3")
NEW_GATE_BYTES = bytes.fromhex("83 79 44 00 0F 97 C0 C3")
OLD_CHECKSUM_BYTES = bytes.fromhex("EF 09 C8 00")
NEW_CHECKSUM_BYTES = bytes.fromhex("03 02 C8 00")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def backup_has_required_pair(manifest: dict) -> tuple[bool, str]:
    backup = manifest.get("backup") or {}
    directory = Path(backup.get("directory", ""))
    if not directory.exists():
        return False, f"备份目录不存在：{directory}"
    client = directory / "SRO_Client.exe"
    gs = directory / "8-SR_GameServer.exe"
    if not client.exists() or not gs.exists():
        return False, "备份目录中必须同时存在 SRO_Client.exe 和 8-SR_GameServer.exe"
    return True, str(directory)


def main() -> int:
    parser = argparse.ArgumentParser(description="客户端 0xCC 队员按钮 gate apply 门禁；默认不写。")
    parser.add_argument("--round", default=DEFAULT_ROUND, help="轮次名")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="本轮冻结 manifest")
    parser.add_argument("--write", action="store_true", help="真正写入；默认只做门禁和计划输出")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    manifest_path = Path(args.manifest)
    checks: list[dict] = []

    def add(name: str, status: str, detail: str, evidence: dict | None = None) -> None:
        checks.append({"name": name, "status": status, "detail": detail, "evidence": evidence or {}})

    if args.round != DEFAULT_ROUND:
        add("round_matches_expected", "FAIL", "轮次名不匹配，拒绝写入。", {"actual": args.round, "expected": DEFAULT_ROUND})
        return emit(args.json, "BLOCKED", target, checks)
    add("round_matches_expected", "PASS", "轮次名匹配。", {"round": args.round})

    if not target.exists():
        add("target_exists", "FAIL", f"目标客户端不存在：{target}")
        return emit(args.json, "BLOCKED", target, checks)
    if not manifest_path.exists():
        add("manifest_exists", "FAIL", f"manifest 不存在：{manifest_path}")
        return emit(args.json, "BLOCKED", target, checks)

    try:
        manifest = read_manifest(manifest_path)
        add("manifest_loaded", "PASS", "已读取 manifest。", {"manifest": str(manifest_path), "round": manifest.get("round")})
    except Exception as exc:
        add("manifest_loaded", "FAIL", f"manifest 无法解析：{exc}")
        return emit(args.json, "BLOCKED", target, checks)

    ok_backup, backup_detail = backup_has_required_pair(manifest)
    add("backup_pair_exists", "PASS" if ok_backup else "FAIL", "已确认本轮 EXE/GS 双文件备份。" if ok_backup else backup_detail, {"backup": backup_detail})
    if not ok_backup:
        return emit(args.json, "BLOCKED", target, checks)

    file_hash = sha256_file(target)
    data = bytearray(target.read_bytes())
    gate = bytes(data[RAW_GATE : RAW_GATE + 8])
    checksum = bytes(data[RAW_CHECKSUM : RAW_CHECKSUM + 4])
    add("target_hash_known", "PASS" if file_hash in {EXPECTED_APPLIED_HASH, EXPECTED_PRE_PHASE2_HASH} else "FAIL", "目标 hash 是已知 Phase2 或写前基线。" if file_hash in {EXPECTED_APPLIED_HASH, EXPECTED_PRE_PHASE2_HASH} else "目标 hash 不在允许集合，拒绝写入。", {"actual_sha256": file_hash})

    if gate == NEW_GATE_BYTES and checksum == NEW_CHECKSUM_BYTES:
        add(
            "patch_state",
            "PASS",
            "目标已经是 Phase2 +0x44 gate 和对应 checksum，无需写入。",
            {"gate_raw_offset": hex(RAW_GATE), "gate_bytes": gate.hex(" ").upper(), "checksum_raw_offset": hex(RAW_CHECKSUM), "checksum_bytes": checksum.hex(" ").upper()},
        )
        status = "DONE_WITH_CONCERNS" if not args.write else "DONE"
        add("write_mode", "INFO", "默认不写；当前已是目标字节。" if not args.write else "传入 --write，但无需写入。")
        return emit(args.json, status, target, checks)

    if gate != OLD_GATE_BYTES:
        add("old_bytes_match", "FAIL", "目标 gate 既不是预期旧字节，也不是目标新字节，拒绝写入。", {"raw_offset": hex(RAW_GATE), "actual": gate.hex(" ").upper(), "expected_old": OLD_GATE_BYTES.hex(" ").upper()})
        return emit(args.json, "BLOCKED", target, checks)

    if checksum != OLD_CHECKSUM_BYTES:
        add(
            "old_checksum_match",
            "FAIL",
            "目标 checksum 不符合 Phase2 写前预期，拒绝写入。",
            {"raw_offset": hex(RAW_CHECKSUM), "actual": checksum.hex(" ").upper(), "expected_old": OLD_CHECKSUM_BYTES.hex(" ").upper()},
        )
        return emit(args.json, "BLOCKED", target, checks)

    add("old_bytes_match", "PASS", "目标 gate/checksum 符合预期旧字节，可计划写入。", {"gate_raw_offset": hex(RAW_GATE), "gate_old": OLD_GATE_BYTES.hex(" ").upper(), "gate_new": NEW_GATE_BYTES.hex(" ").upper(), "checksum_raw_offset": hex(RAW_CHECKSUM), "checksum_old": OLD_CHECKSUM_BYTES.hex(" ").upper(), "checksum_new": NEW_CHECKSUM_BYTES.hex(" ").upper()})
    if not args.write:
        add("write_mode", "INFO", "默认不写；如需写入必须显式传入 --write。")
        return emit(args.json, "DONE_WITH_CONCERNS", target, checks)

    data[RAW_GATE : RAW_GATE + 8] = NEW_GATE_BYTES
    data[RAW_CHECKSUM : RAW_CHECKSUM + 4] = NEW_CHECKSUM_BYTES
    target.write_bytes(data)
    add("write_done", "PASS", "已写入客户端 gate 和 checksum 字节。", {"new_sha256": sha256_file(target)})
    return emit(args.json, "DONE", target, checks)


def emit(as_json: bool, status: str, target: Path, checks: list[dict]) -> int:
    if any(c["status"] == "FAIL" for c in checks):
        status = "BLOCKED"
    payload = {"script": Path(__file__).name, "status": status, "target": str(target), "checks": checks}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"状态：{status}")
        for c in checks:
            print(f"- [{c['status']}] {c['name']}: {c['detail']}")
    return 1 if status == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
