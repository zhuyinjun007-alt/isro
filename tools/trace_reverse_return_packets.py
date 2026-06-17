# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path


DEFAULT_TARGET = Path(r"F:\CSRO客户端\SRO_Client.exe")
DEFAULT_REFERENCE = Path(r"F:\ISRO客户端国服\sro_client.exe")
EXPECTED_PHASE2_HASH = "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E"
OPCODES = {
    "party_position_list_request": 0x759F,
    "saved_position_list_request": 0x7600,
    "party_position_list_response": 0xB59F,
    "saved_position_list_response": 0xB600,
    "party_position_move": 0x3213,
    "user_appoint_move_family": 0x705A,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def offsets(data: bytes, value: int) -> list[int]:
    needle = struct.pack("<H", value)
    found: list[int] = []
    pos = data.find(needle)
    while pos >= 0:
        found.append(pos)
        pos = data.find(needle, pos + 1)
    return found


def summarize(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "exists": False}
    data = path.read_bytes()
    rows = {}
    for name, opcode in OPCODES.items():
        found = offsets(data, opcode)
        rows[name] = {
            "opcode": hex(opcode),
            "count": len(found),
            "first_offsets": [hex(x) for x in found[:12]],
        }
    return {"path": str(path), "exists": True, "sha256": sha256_file(path), "opcodes": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="只读扫描客户端返回新增功能相关协议号静态线索。")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE), help="ISRO 客户端参考 EXE 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    reference = Path(args.reference)
    target_summary = summarize(target)
    reference_summary = summarize(reference)
    checks = []

    if not target_summary.get("exists"):
        checks.append({"name": "target_exists", "status": "FAIL", "detail": f"目标客户端不存在：{target}"})
    else:
        checks.append({"name": "target_hash", "status": "PASS" if target_summary.get("sha256") == EXPECTED_PHASE2_HASH else "WARN", "detail": "当前 EXE hash 与 Phase2 冻结值一致。" if target_summary.get("sha256") == EXPECTED_PHASE2_HASH else "当前 EXE hash 与 Phase2 冻结值不一致。"})
        for name, row in target_summary["opcodes"].items():
            checks.append({"name": name, "status": "INFO" if row["count"] else "WARN", "detail": f"静态扫描 opcode {row['opcode']} 出现 {row['count']} 次。", "evidence": row})

    if not reference_summary.get("exists"):
        checks.append({"name": "reference_exists", "status": "WARN", f"detail": f"参考 ISRO 客户端不存在：{reference}"})
    else:
        checks.append({"name": "reference_scanned", "status": "INFO", "detail": "已扫描 ISRO 客户端参考文件；仅作静态对照。", "evidence": {"sha256": reference_summary.get("sha256")}})

    checks.append({"name": "runtime_packet_gap", "status": "WARN", "detail": "本脚本未抓包、未 hook 发送函数；静态 opcode 存在不能证明点击 0xCC/0xCF 已发出正确请求。"})

    failed = any(c["status"] == "FAIL" for c in checks)
    status = "BLOCKED" if failed else "DONE_WITH_CONCERNS"
    payload = {"script": Path(__file__).name, "status": status, "target": target_summary, "reference": reference_summary, "checks": checks}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"状态：{status}")
        for c in checks:
            print(f"- [{c['status']}] {c['name']}: {c['detail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
