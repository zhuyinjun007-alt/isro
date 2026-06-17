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
RAW_MESSAGE_MAP_BASE = 0x00ABE9F4
RAW_MESSAGE_MAP_ENTRIES = 0x00ABE9F8
RAW_EXTENSION_HEADER = 0x00C70000
RAW_EXTENSION_ENTRIES = 0x00C70020
EXPECTED_OLD_BASE = 0x00EC21B4
EXPECTED_OLD_ENTRIES = 0x00FFE1E8
KNOWN_BAD_WHOLE_TABLE = 0x012ED000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def u32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def find_pair(data: bytes, button: int, handler: int, start: int, size: int) -> dict:
    window = data[start : min(len(data), start + size)]
    button_b = struct.pack("<I", button)
    handler_b = struct.pack("<I", handler)
    button_pos = window.find(button_b)
    handler_pos = window.find(handler_b)
    return {
        "button": hex(button),
        "handler": hex(handler),
        "button_raw_offset": hex(start + button_pos) if button_pos >= 0 else None,
        "handler_raw_offset": hex(start + handler_pos) if handler_pos >= 0 else None,
        "both_seen_in_window": button_pos >= 0 and handler_pos >= 0,
    }


def row(name: str, status: str, detail: str, evidence: dict | None = None) -> dict:
    return {"name": name, "status": status, "detail": detail, "evidence": evidence or {}}


def main() -> int:
    parser = argparse.ArgumentParser(description="只读追踪当前客户端返回 UI message-map 指针与 0xCC/0xCF 小表线索。")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    results: list[dict] = []
    if not target.exists():
        results.append(row("target_exists", "FAIL", f"目标客户端不存在：{target}"))
        return emit(args.json, target, results)

    data = target.read_bytes()
    file_hash = sha256_file(target)
    active_base = u32(data, RAW_MESSAGE_MAP_BASE)
    active_entries = u32(data, RAW_MESSAGE_MAP_ENTRIES)
    extension_base = u32(data, RAW_EXTENSION_HEADER)
    extension_entries = u32(data, RAW_EXTENSION_HEADER + 4)
    pair_cc = find_pair(data, 0xCC, 0x012DEF50, RAW_EXTENSION_ENTRIES, 0x200)
    pair_cf = find_pair(data, 0xCF, 0x012DF020, RAW_EXTENSION_ENTRIES, 0x200)

    results.append(
        row(
            "target_hash_is_current_phase2_client",
            "PASS" if file_hash == EXPECTED_PHASE2_HASH else "WARN",
            "当前 EXE hash 与 Task1/Phase2 冻结值一致。"
            if file_hash == EXPECTED_PHASE2_HASH
            else "当前 EXE hash 与 Task1/Phase2 冻结值不一致。",
            {"actual_sha256": file_hash, "expected_sha256": EXPECTED_PHASE2_HASH},
        )
    )
    results.append(
        row(
            "active_map_uses_old_csro_entries",
            "PASS" if active_base == EXPECTED_OLD_BASE and active_entries == EXPECTED_OLD_ENTRIES else "FAIL",
            "active base/entries 当前保持旧 CSRO 链路。"
            if active_base == EXPECTED_OLD_BASE and active_entries == EXPECTED_OLD_ENTRIES
            else "active base/entries 未保持旧 CSRO 链路，禁止继续。",
            {"base": hex(active_base) if active_base is not None else None, "entries": hex(active_entries) if active_entries is not None else None},
        )
    )
    results.append(
        row(
            "known_bad_whole_table_not_active",
            "PASS" if active_entries != KNOWN_BAD_WHOLE_TABLE else "FAIL",
            "active entries 未指向已失败的 0x012ED000 整表替换路线。",
            {"known_bad_value": hex(KNOWN_BAD_WHOLE_TABLE)},
        )
    )
    results.append(
        row(
            "extension_header_observed",
            "INFO" if extension_base is not None or extension_entries is not None else "WARN",
            "已读取 0x012ED000 附近小表候选；它当前不是 active entries，只能作为新增按钮候选证据。",
            {"raw_offset": hex(RAW_EXTENSION_HEADER), "base": hex(extension_base) if extension_base is not None else None, "entries": hex(extension_entries) if extension_entries is not None else None},
        )
    )
    results.append(
        row(
            "new_button_0xCC_candidate",
            "INFO" if pair_cc["both_seen_in_window"] else "WARN",
            "0xCC 与 0x012DEF50 在小表候选窗口中同时可见。" if pair_cc["both_seen_in_window"] else "未在小表候选窗口同时确认 0xCC 与 0x012DEF50。",
            pair_cc,
        )
    )
    results.append(
        row(
            "new_button_0xCF_candidate",
            "INFO" if pair_cf["both_seen_in_window"] else "WARN",
            "0xCF 与 0x012DF020 在小表候选窗口中同时可见。" if pair_cf["both_seen_in_window"] else "未在小表候选窗口同时确认 0xCF 与 0x012DF020。",
            pair_cf,
        )
    )
    results.append(
        row(
            "old_button_runtime_slots",
            "INFO",
            "旧报告记录旧按钮 0xC8/0xC9/0xCA/0xCB 仍走原 CSRO runtime slots；本脚本未解析运行时 initializer，只核 active map 不复用整表替换。",
            {"expected_old_handlers_from_reports": {"0xC8": "0x703F10", "0xC9": "0x7040E0", "0xCA": "0x70AB50", "0xCB": "0x7041D0"}},
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
