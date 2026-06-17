# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


DEFAULT_TARGET = Path(r"F:\CSRO客户端\SRO_Client.exe")
EXPECTED_PHASE2_HASH = "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E"
RAW_CALL = 0x00C66BC6
RAW_GATE = 0x00C6F9C0
CALL_TO_GATE = bytes.fromhex("E8 F5 8D 00 00")
GATE_LIST_COUNT = bytes.fromhex("83 79 44 00 0F 97 C0 C3")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="只读校验 0xCC 队员按钮 gate 是否为当前 Phase2 口径。")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    checks: list[dict] = []
    if not target.exists():
        checks.append({"name": "target_exists", "status": "FAIL", "detail": f"目标客户端不存在：{target}"})
        return emit(args.json, target, checks)

    data = target.read_bytes()
    file_hash = sha256_file(target)
    call = data[RAW_CALL : RAW_CALL + 5]
    gate = data[RAW_GATE : RAW_GATE + 8]
    checks.append({"name": "target_hash", "status": "PASS" if file_hash == EXPECTED_PHASE2_HASH else "WARN", "detail": "当前 EXE hash 与 Phase2 冻结值一致。" if file_hash == EXPECTED_PHASE2_HASH else "当前 EXE hash 与 Phase2 冻结值不一致。", "evidence": {"actual_sha256": file_hash}})
    checks.append({"name": "call_site", "status": "PASS" if call == CALL_TO_GATE else "FAIL", "detail": "0xCC enable call 指向专用 gate。", "evidence": {"raw_offset": hex(RAW_CALL), "actual": call.hex(" ").upper(), "expected": CALL_TO_GATE.hex(" ").upper()}})
    checks.append({"name": "gate_bytes", "status": "PASS" if gate == GATE_LIST_COUNT else "FAIL", "detail": "gate 为 state_global+0x44 > 0。", "evidence": {"raw_offset": hex(RAW_GATE), "actual": gate.hex(" ").upper(), "expected": GATE_LIST_COUNT.hex(" ").upper()}})
    checks.append({"name": "runtime_acceptance", "status": "WARN", "detail": "静态 gate 通过不等于游戏内置灰成功；需验证单人置灰、2 人组队启用、旧 CSRO 返回功能和无 dump/FatalLog。"})
    return emit(args.json, target, checks)


def emit(as_json: bool, target: Path, checks: list[dict]) -> int:
    failed = any(c["status"] == "FAIL" for c in checks)
    warned = any(c["status"] == "WARN" for c in checks)
    status = "BLOCKED" if failed else ("DONE_WITH_CONCERNS" if warned else "DONE")
    payload = {"script": Path(__file__).name, "status": status, "target": str(target), "checks": checks}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"状态：{status}")
        for c in checks:
            print(f"- [{c['status']}] {c['name']}: {c['detail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
