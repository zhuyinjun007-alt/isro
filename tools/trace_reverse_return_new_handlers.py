# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path


DEFAULT_TARGET = Path(r"F:\CSRO客户端\SRO_Client.exe")
EXPECTED_PHASE2_HASH = "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E"
RAW_EXTENSION_ENTRIES = 0x00C70020
HANDLER_CC = 0x012DEF50
HANDLER_CF = 0x012DF020


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def find_all(data: bytes, needle: bytes, start: int, size: int) -> list[int]:
    end = min(len(data), start + size)
    pos = data.find(needle, start, end)
    found: list[int] = []
    while pos >= 0:
        found.append(pos)
        pos = data.find(needle, pos + 1, end)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="只读追踪 0xCC/0xCF 新增 handler 静态候选。")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    rows: list[dict] = []
    if not target.exists():
        rows.append({"name": "target_exists", "status": "FAIL", "detail": f"目标客户端不存在：{target}"})
        return emit(args.json, target, rows)

    data = target.read_bytes()
    file_hash = sha256_file(target)
    window_size = 0x400
    cc_button = find_all(data, struct.pack("<I", 0xCC), RAW_EXTENSION_ENTRIES, window_size)
    cf_button = find_all(data, struct.pack("<I", 0xCF), RAW_EXTENSION_ENTRIES, window_size)
    cc_handler = find_all(data, struct.pack("<I", HANDLER_CC), RAW_EXTENSION_ENTRIES, window_size)
    cf_handler = find_all(data, struct.pack("<I", HANDLER_CF), RAW_EXTENSION_ENTRIES, window_size)

    rows.append({"name": "target_hash", "status": "PASS" if file_hash == EXPECTED_PHASE2_HASH else "WARN", "detail": "当前 EXE hash 与 Phase2 冻结值一致。" if file_hash == EXPECTED_PHASE2_HASH else "当前 EXE hash 与 Phase2 冻结值不一致。", "evidence": {"actual_sha256": file_hash}})
    rows.append({"name": "handler_candidate_0xCC", "status": "INFO" if cc_button and cc_handler else "WARN", "detail": "在候选窗口看到 0xCC 与 handler 0x012DEF50。" if cc_button and cc_handler else "未能在候选窗口完整确认 0xCC handler。", "evidence": {"button_offsets": [hex(x) for x in cc_button], "handler_offsets": [hex(x) for x in cc_handler]}})
    rows.append({"name": "handler_candidate_0xCF", "status": "INFO" if cf_button and cf_handler else "WARN", "detail": "在候选窗口看到 0xCF 与 handler 0x012DF020。" if cf_button and cf_handler else "未能在候选窗口完整确认 0xCF handler。", "evidence": {"button_offsets": [hex(x) for x in cf_button], "handler_offsets": [hex(x) for x in cf_handler]}})
    rows.append({"name": "active_dispatch_gap", "status": "WARN", "detail": "静态候选存在不等于 active dispatch 已闭合；本脚本不写二进制，不证明点击 0xCC/0xCF 会到达这些 handler。"})
    rows.append({"name": "old_buttons_boundary", "status": "INFO", "detail": "旧按钮 0xC8/0xC9/0xCA/0xCB 必须保持旧 CSRO 链路；本脚本只追踪新增 0xCC/0xCF 候选。"})
    return emit(args.json, target, rows)


def emit(as_json: bool, target: Path, rows: list[dict]) -> int:
    failed = any(r["status"] == "FAIL" for r in rows)
    warned = any(r["status"] == "WARN" for r in rows)
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
