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
GATE_LIST_COUNT = bytes.fromhex("83 79 44 00 0F 97 C0 C3")
GATE_BAD_30 = bytes.fromhex("83 79 30 02 0F 9D C0 C3")


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


def evidence(name: str, status: str, detail: str, extra: dict | None = None) -> dict:
    return {"name": name, "status": status, "detail": detail, "evidence": extra or {}}


def main() -> int:
    parser = argparse.ArgumentParser(description="只读定位 0xCC 队员位置按钮 enable 来源。")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    rows: list[dict] = []
    if not target.exists():
        rows.append(evidence("target_exists", "FAIL", f"目标客户端不存在：{target}"))
        return emit(args.json, target, rows)

    data = target.read_bytes()
    file_hash = sha256_file(target)
    call_bytes = read_bytes(data, RAW_PARTY_ENABLE_CALL, 5)
    gate_bytes = read_bytes(data, RAW_PARTY_GATE_STUB, 8)

    rows.append(
        evidence(
            "target_hash",
            "PASS" if file_hash == EXPECTED_PHASE2_HASH else "WARN",
            "当前 EXE hash 与 Phase2 冻结值一致。" if file_hash == EXPECTED_PHASE2_HASH else "当前 EXE hash 与 Phase2 冻结值不一致。",
            {"actual_sha256": file_hash, "expected_sha256": EXPECTED_PHASE2_HASH},
        )
    )
    rows.append(
        evidence(
            "button_0xCC_enable_call_site",
            "PASS" if call_bytes == CALL_TO_GATE else "FAIL",
            "0xCC enable call site 当前进入 0x012EC9C0 专用 gate。",
            {"raw_offset": hex(RAW_PARTY_ENABLE_CALL), "actual": call_bytes.hex(" ").upper() if call_bytes else None, "expected": CALL_TO_GATE.hex(" ").upper()},
        )
    )
    rows.append(
        evidence(
            "button_0xCC_gate_source",
            "PASS" if gate_bytes == GATE_LIST_COUNT else "FAIL",
            "专用 gate 读取 state_global+0x44，并以 >0 判定可用。",
            {"raw_offset": hex(RAW_PARTY_GATE_STUB), "actual": gate_bytes.hex(" ").upper() if gate_bytes else None, "expected": GATE_LIST_COUNT.hex(" ").upper()},
        )
    )
    rows.append(
        evidence(
            "failed_state_global_0x30_route",
            "PASS" if gate_bytes != GATE_BAD_30 else "FAIL",
            "当前未复用 Phase11A 已失败的 state_global+0x30 >= 2 路线。",
            {"known_bad_bytes": GATE_BAD_30.hex(" ").upper()},
        )
    )
    rows.append(
        evidence(
            "source_chain_from_reports",
            "INFO",
            "Phase2 报告记录 +0x44 是队员列表计数：reset 先看 [state+0x44]，遍历 [state+0x40] 链表，删除节点后 [state+0x44] -= 1。",
            {"report": "reports/旧/Phase2执行记录-队员置灰改用列表计数gate-20260617-0918.md"},
        )
    )
    rows.append(
        evidence(
            "runtime_gap",
            "WARN",
            "缺少本轮运行时断点/游戏内证据，不能证明单人 UI 已实际置灰。",
        )
    )
    return emit(args.json, target, rows)


def emit(as_json: bool, target: Path, rows: list[dict]) -> int:
    failed = [r for r in rows if r["status"] == "FAIL"]
    warned = [r for r in rows if r["status"] == "WARN"]
    status = "BLOCKED" if failed else ("DONE_WITH_CONCERNS" if warned else "DONE")
    payload = {"script": Path(__file__).name, "status": status, "target": str(target), "results": rows}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"状态：{status}")
        for r in rows:
            print(f"- [{r['status']}] {r['name']}: {r['detail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
