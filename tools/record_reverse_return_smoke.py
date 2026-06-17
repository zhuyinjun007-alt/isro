from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from isro_return_common import CSRO_EXE, CSRO_GS, EVIDENCE_DIR, ROUND, file_info, write_json


SMOKE_ITEMS = [
    "第一次右键返回卷轴 UI 正常出现",
    "关闭后第二次右键返回卷轴 UI 正常出现",
    "旧 CSRO 按钮 0xC8/0xC9/0xCA/0xCB 功能仍可用",
    "单人未组队时 0xCC 移动至队员位置灰色不可选",
    "两人及以上组队时 0xCC 可选",
    "0xCC 点击后不闪退并进入预期链路",
    "0xCF 点击后不闪退并进入预期链路",
    "同时间段无新增客户端 dump",
    "同时间段无新增 GS FatalLog",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an end-to-end smoke-test record template.")
    parser.add_argument("--round", default=ROUND)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true", help="write smoke evidence template")
    args = parser.parse_args()

    payload = {
        "round": args.round,
        "created_at": datetime.now().astimezone().isoformat(),
        "status": "manual_smoke_required",
        "live_files": [file_info(CSRO_EXE), file_info(CSRO_GS)],
        "items": [{"name": item, "result": "pending", "evidence": ""} for item in SMOKE_ITEMS],
        "notes": [
            "This script records the smoke-test checklist; it does not launch the game client.",
            "Fill results after manual in-game validation.",
        ],
    }

    if args.write:
        out = EVIDENCE_DIR / "2026-06-17-phase-isro-new-return-actions-smoke.json"
        write_json(out, payload)
        payload["written_to"] = str(out)

    if args.json:
        import json

        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in payload["items"]:
            print(f"[pending] {item['name']}")
        if "written_to" in payload:
            print(f"written: {payload['written_to']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
