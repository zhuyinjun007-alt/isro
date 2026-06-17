# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path


DEFAULT_TARGET = Path(r"F:\CSRO客户端\SRO_Client.exe")
DEFAULT_MANIFEST = Path(r"evidence\2026-06-17-phase-isro-new-return-actions-manifest.json")
EXPECTED_PHASE2_HASH = "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E"

RAW_MESSAGE_MAP_BASE = 0x00ABE9F4
RAW_MESSAGE_MAP_ENTRIES = 0x00ABE9F8
EXPECTED_OLD_BASE = 0x00EC21B4
EXPECTED_OLD_ENTRIES = 0x00FFE1E8
KNOWN_BAD_WHOLE_TABLE = 0x012ED000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def read_u32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def item(name: str, status: str, detail: str, evidence: dict | None = None) -> dict:
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "evidence": evidence or {},
    }


def load_manifest(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="只读检查 Phase10/Phase2 当前客户端入口和旧 CSRO message-map 基线。"
    )
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="本轮冻结 manifest")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    target = Path(args.target)
    manifest_path = Path(args.manifest)
    results: list[dict] = []

    if not target.exists():
        results.append(item("target_exists", "FAIL", f"目标客户端不存在：{target}"))
        return emit(args.json, target, manifest_path, results)

    data = target.read_bytes()
    file_hash = sha256_file(target)
    manifest = load_manifest(manifest_path)

    results.append(
        item(
            "target_hash_is_current_phase2_client",
            "PASS" if file_hash == EXPECTED_PHASE2_HASH else "WARN",
            "当前 EXE hash 与 Task1/Phase2 冻结值一致。"
            if file_hash == EXPECTED_PHASE2_HASH
            else "当前 EXE hash 与已知 Phase2 冻结值不一致，只能继续只读采证，不能写入。",
            {"actual_sha256": file_hash, "expected_sha256": EXPECTED_PHASE2_HASH},
        )
    )

    if manifest is None:
        results.append(item("manifest_loaded", "WARN", "未能读取本轮 manifest；只读检查继续，但 apply 门禁会拒绝。"))
    else:
        results.append(
            item(
                "manifest_loaded",
                "PASS",
                "已读取本轮 manifest。",
                {"manifest": str(manifest_path), "round": manifest.get("round")},
            )
        )

    active_base = read_u32(data, RAW_MESSAGE_MAP_BASE)
    active_entries = read_u32(data, RAW_MESSAGE_MAP_ENTRIES)

    results.append(
        item(
            "message_map_base_restored_to_old_csro",
            "PASS" if active_base == EXPECTED_OLD_BASE else "FAIL",
            "active message-map base 保持旧 CSRO 链路。"
            if active_base == EXPECTED_OLD_BASE
            else "active message-map base 不等于旧 CSRO 值，旧链路可能被污染。",
            {
                "raw_offset": hex(RAW_MESSAGE_MAP_BASE),
                "actual": hex(active_base) if active_base is not None else None,
                "expected": hex(EXPECTED_OLD_BASE),
            },
        )
    )
    results.append(
        item(
            "message_map_entries_restored_to_old_csro",
            "PASS" if active_entries == EXPECTED_OLD_ENTRIES else "FAIL",
            "active message-map entries 保持旧 CSRO 表。"
            if active_entries == EXPECTED_OLD_ENTRIES
            else "active message-map entries 不等于旧 CSRO 表，禁止继续。",
            {
                "raw_offset": hex(RAW_MESSAGE_MAP_ENTRIES),
                "actual": hex(active_entries) if active_entries is not None else None,
                "expected": hex(EXPECTED_OLD_ENTRIES),
            },
        )
    )
    results.append(
        item(
            "whole_message_map_replacement_not_active",
            "PASS" if active_entries != KNOWN_BAD_WHOLE_TABLE else "FAIL",
            "未复用已失败的整张 message-map entries 替换路线。"
            if active_entries != KNOWN_BAD_WHOLE_TABLE
            else "active entries 指向 0x012ED000，这是已失败路线。",
            {"known_bad_value": hex(KNOWN_BAD_WHOLE_TABLE)},
        )
    )
    results.append(
        item(
            "right_click_entry_0x21",
            "INFO",
            "旧报告已记录真实右键入口为 SetMsgBoxHandler arg0=0x21；本脚本不做动态断点，不能单独证明运行时入口。",
            {
                "source_reports": [
                    "reports/旧/CSRO返回功能全局反思报告-20260616.md",
                    "reports/旧/ISRO-CSRO返回功能对照表-20260616.md",
                    "踩过的坑.md",
                ]
            },
        )
    )
    results.append(
        item(
            "gs_checks_out_of_scope",
            "INFO",
            "本子代理只做客户端侧脚本；本检查不读取、不修改 D:\\CSRO\\8-SR_GameServer.exe。",
        )
    )

    return emit(args.json, target, manifest_path, results)


def emit(as_json: bool, target: Path, manifest: Path, results: list[dict]) -> int:
    failed = [r for r in results if r["status"] == "FAIL"]
    warned = [r for r in results if r["status"] == "WARN"]
    status = "BLOCKED" if failed else ("DONE_WITH_CONCERNS" if warned else "DONE")
    payload = {
        "script": Path(__file__).name,
        "status": status,
        "target": str(target),
        "manifest": str(manifest),
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
