# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


DEFAULT_TARGET = Path(r"F:\CSRO客户端\SRO_Client.exe")
EXPECTED_PHASE2_HASH = "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E"

RAW_PARTY_ENABLE_CALL = 0x00C66BC6
RAW_PARTY_GATE_STUB = 0x00C6F9C0

CALL_TO_GATE = bytes.fromhex("E8 F5 8D 00 00")
CALL_TO_FAILED_FLAG = bytes.fromhex("E8 85 82 79 FF")
GATE_PHASE2_LIST_COUNT = bytes.fromhex("83 79 44 00 0F 97 C0 C3")
GATE_PHASE11A_FAILED_30 = bytes.fromhex("83 79 30 02 0F 9D C0 C3")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def read_bytes(data: bytes, offset: int, length: int) -> bytes | None:
    if offset < 0 or offset + length > len(data):
        return None
    return data[offset : offset + length]


def result(name: str, status: str, detail: str, evidence: dict | None = None) -> dict:
    return {"name": name, "status": status, "detail": detail, "evidence": evidence or {}}


def main() -> int:
    parser = argparse.ArgumentParser(description="只读检查 0xCC 队员按钮 enable gate 当前客户端字节。")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    results: list[dict] = []
    if not target.exists():
        results.append(result("target_exists", "FAIL", f"目标客户端不存在：{target}"))
        return emit(args.json, target, results)

    data = target.read_bytes()
    file_hash = sha256_file(target)
    call_bytes = read_bytes(data, RAW_PARTY_ENABLE_CALL, 5)
    gate_bytes = read_bytes(data, RAW_PARTY_GATE_STUB, 8)

    results.append(
        result(
            "target_hash_is_current_phase2_client",
            "PASS" if file_hash == EXPECTED_PHASE2_HASH else "WARN",
            "当前 EXE hash 与 Phase2/Task1 冻结值一致。"
            if file_hash == EXPECTED_PHASE2_HASH
            else "当前 EXE hash 与 Phase2/Task1 冻结值不一致；禁止把本检查当写入依据。",
            {"actual_sha256": file_hash, "expected_sha256": EXPECTED_PHASE2_HASH},
        )
    )
    results.append(
        result(
            "party_enable_call_targets_private_gate",
            "PASS" if call_bytes == CALL_TO_GATE else "FAIL",
            "0xCC enable call 当前指向专用 gate stub。"
            if call_bytes == CALL_TO_GATE
            else "0xCC enable call 未指向专用 gate stub。",
            {
                "raw_offset": hex(RAW_PARTY_ENABLE_CALL),
                "actual": call_bytes.hex(" ").upper() if call_bytes else None,
                "expected": CALL_TO_GATE.hex(" ").upper(),
            },
        )
    )
    results.append(
        result(
            "failed_phase1_call_not_active",
            "PASS" if call_bytes != CALL_TO_FAILED_FLAG else "FAIL",
            "未复用 Phase1 已失败的仅恢复 0x00A7BE50 call 路线。"
            if call_bytes != CALL_TO_FAILED_FLAG
            else "当前命中 Phase1 已失败路线：call 0x00A7BE50。",
            {"known_bad_bytes": CALL_TO_FAILED_FLAG.hex(" ").upper()},
        )
    )
    results.append(
        result(
            "party_gate_uses_list_count_0x44",
            "PASS" if gate_bytes == GATE_PHASE2_LIST_COUNT else "FAIL",
            "专用 gate 当前为 state_global+0x44 > 0。"
            if gate_bytes == GATE_PHASE2_LIST_COUNT
            else "专用 gate 不是 Phase2 的 +0x44 列表计数口径。",
            {
                "raw_offset": hex(RAW_PARTY_GATE_STUB),
                "actual": gate_bytes.hex(" ").upper() if gate_bytes else None,
                "expected": GATE_PHASE2_LIST_COUNT.hex(" ").upper(),
            },
        )
    )
    results.append(
        result(
            "failed_phase11a_gate_not_active",
            "PASS" if gate_bytes != GATE_PHASE11A_FAILED_30 else "FAIL",
            "未复用 Phase11A 已失败的 state_global+0x30 >= 2 gate。",
            {"known_bad_bytes": GATE_PHASE11A_FAILED_30.hex(" ").upper()},
        )
    )
    results.append(
        result(
            "runtime_status_not_proven",
            "INFO",
            "本脚本只证明当前客户端字节，不证明游戏内单人置灰或 2 人组队启用；仍需游戏内验证。",
        )
    )
    return emit(args.json, target, results)


def emit(as_json: bool, target: Path, results: list[dict]) -> int:
    failed = [r for r in results if r["status"] == "FAIL"]
    warned = [r for r in results if r["status"] == "WARN"]
    status = "BLOCKED" if failed else ("DONE_WITH_CONCERNS" if warned else "DONE")
    payload = {
        "script": Path(__file__).name,
        "status": status,
        "target": str(target),
        "summary": {"pass": count(results, "PASS"), "warn": count(results, "WARN"), "fail": count(results, "FAIL"), "info": count(results, "INFO")},
        "results": results,
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"状态：{status}")
        for r in results:
            print(f"- [{r['status']}] {r['name']}: {r['detail']}")
    return 1 if failed else 0


def count(results: list[dict], status: str) -> int:
    return sum(1 for r in results if r["status"] == status)


if __name__ == "__main__":
    sys.exit(main())
