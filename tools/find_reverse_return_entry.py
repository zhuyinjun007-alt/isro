# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


DEFAULT_TARGET = Path(r"F:\CSRO客户端\SRO_Client.exe")
EXPECTED_PHASE2_HASH = "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="整理返回卷轴真实右键入口的只读证据，不做动态断点。")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="CSRO 客户端 EXE 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--strict", action="store_true", help="严格模式：缺少动态证据时返回非零")
    args = parser.parse_args()

    target = Path(args.target)
    observations: list[dict] = []
    if not target.exists():
        payload = {"script": Path(__file__).name, "status": "BLOCKED", "error": f"目标客户端不存在：{target}"}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload["error"])
        return 1

    file_hash = sha256_file(target)
    observations.append(
        {
            "name": "target_hash",
            "status": "PASS" if file_hash == EXPECTED_PHASE2_HASH else "WARN",
            "detail": "当前 EXE hash 与 Task1/Phase2 冻结值一致。"
            if file_hash == EXPECTED_PHASE2_HASH
            else "当前 EXE hash 与冻结值不一致，入口结论只能作为历史证据对照。",
            "evidence": {"actual_sha256": file_hash, "expected_sha256": EXPECTED_PHASE2_HASH},
        }
    )
    observations.append(
        {
            "name": "right_click_entry",
            "status": "PASS",
            "detail": "已读旧报告一致记录：真实右键返回卷轴进入 SetMsgBoxHandler 时 arg0=0x21。",
            "evidence": {
                "entry_type": "0x21",
                "source_reports": [
                    "踩过的坑.md",
                    "reports/旧/ISRO-CSRO返回功能对照表-20260616.md",
                    "reports/旧/CSRO返回功能全局反思报告-20260616.md",
                ],
            },
        }
    )
    observations.append(
        {
            "name": "known_wrong_entries",
            "status": "PASS",
            "detail": "0x2A/0x2B/0x25/0x28 是历史误判或非真实右键入口，不能作为 live 入口依据。",
            "evidence": {"forbidden_as_live_entry": ["0x2A", "0x2B", "0x25", "0x28"]},
        }
    )
    observations.append(
        {
            "name": "dynamic_trace",
            "status": "WARN",
            "detail": "本脚本未附加进程、未下断点、未复测运行时 arg0；动态证据仍待补。",
        }
    )

    status = "DONE_WITH_CONCERNS"
    payload = {"script": Path(__file__).name, "status": status, "target": str(target), "observations": observations}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"状态：{status}")
        for row in observations:
            print(f"- [{row['status']}] {row['name']}: {row['detail']}")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
