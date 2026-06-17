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
EXPECTED_PHASE2_HASH = "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="0xCC/0xCF 新 handler apply 硬门禁；当前无足够写入证据，默认拒绝。")
    parser.add_argument("--round", default=DEFAULT_ROUND, help="轮次名")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="本轮冻结 manifest")
    parser.add_argument("--write", action="store_true", help="请求写入；仍需完整写入计划，否则拒绝")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    manifest_path = Path(args.manifest)
    checks: list[dict] = []

    def add(name: str, status: str, detail: str, evidence: dict | None = None) -> None:
        checks.append({"name": name, "status": status, "detail": detail, "evidence": evidence or {}})

    if args.round != DEFAULT_ROUND:
        add("round_matches_expected", "FAIL", "轮次名不匹配。", {"actual": args.round, "expected": DEFAULT_ROUND})
    else:
        add("round_matches_expected", "PASS", "轮次名匹配。")

    if not target.exists():
        add("target_exists", "FAIL", f"目标客户端不存在：{target}")
    else:
        file_hash = sha256_file(target)
        add("target_hash_known", "PASS" if file_hash == EXPECTED_PHASE2_HASH else "FAIL", "目标 hash 与当前冻结客户端一致。" if file_hash == EXPECTED_PHASE2_HASH else "目标 hash 与当前冻结客户端不一致，拒绝。", {"actual_sha256": file_hash, "expected_sha256": EXPECTED_PHASE2_HASH})

    if not manifest_path.exists():
        add("manifest_exists", "FAIL", f"manifest 不存在：{manifest_path}")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            backup_dir = Path((manifest.get("backup") or {}).get("directory", ""))
            add("manifest_loaded", "PASS", "已读取 manifest。", {"round": manifest.get("round")})
            add("backup_pair_exists", "PASS" if (backup_dir / "SRO_Client.exe").exists() and (backup_dir / "8-SR_GameServer.exe").exists() else "FAIL", "已确认本轮 EXE/GS 双文件备份。" if (backup_dir / "SRO_Client.exe").exists() and (backup_dir / "8-SR_GameServer.exe").exists() else "备份不完整，拒绝。", {"backup_dir": str(backup_dir)})
        except Exception as exc:
            add("manifest_loaded", "FAIL", f"manifest 无法解析：{exc}")

    add(
        "write_plan_available",
        "FAIL",
        "缺少可复核的 VA/raw offset/old bytes/new bytes 与运行时证据；本脚本拒绝写入 0xCC/0xCF handler。",
        {
            "required_evidence": [
                "0xCC/0xCF active dispatch 唯一路径",
                "旧按钮 0xC8/0xC9/0xCA/0xCB 不受影响证明",
                "发包语义与 ISRO 对照",
                "写入 manifest 中每个字节的 old/new 计划",
            ]
        },
    )
    if not args.write:
        add("write_mode", "INFO", "默认不写；即使传入 --write，当前也会因证据不足拒绝。")
    else:
        add("write_mode", "INFO", "已传入 --write，但硬门禁未满足，未写入。")

    return emit(args.json, "BLOCKED", target, checks)


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
    return 1


if __name__ == "__main__":
    sys.exit(main())
