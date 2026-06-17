from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trace_isro_gs_return_paths import (
    DEFAULT_CSRO_GS,
    DEFAULT_ISRO_GS,
    ROUND,
    file_info,
    marker_present,
    scan_file,
)


ACTIVE_FILTER_SLOT_RAW = 0x7CA560
ACTIVE_FILTER_SLOT_VA = 0x00BCA560
EXPECTED_OLD_CSRO_FILTER = 0x004C8410
KNOWN_FAILED_NEW_FILTER = 0x00E56000
REQUIRED_MARKERS = ("0x3213", "0x705A", "0x759F", "0x7600", "0xB59F", "0xB600", "9114", "24298")


def read_u32(path: Path, raw: int) -> int | None:
    if not path.exists() or raw < 0 or raw + 4 > path.stat().st_size:
        return None
    with path.open("rb") as f:
        f.seek(raw)
        return struct.unpack("<I", f.read(4))[0]


def check_item(name: str, status: str, detail: str, *, severity: str = "required") -> dict[str, Any]:
    return {"name": name, "status": status, "severity": severity, "detail": detail}


def marker_counts(scan: dict[str, Any], key: str) -> int:
    marker = scan.get("markers", {}).get(key)
    if not marker:
        return 0
    return sum(pattern["count"] for pattern in marker["patterns"].values())


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    isro_path = Path(args.isro_gs)
    csro_path = Path(args.csro_gs)
    isro_scan = scan_file(isro_path, max_occurrences=args.max_occurrences, include_all=False, context=8)
    csro_scan = scan_file(csro_path, max_occurrences=args.max_occurrences, include_all=False, context=8)
    checks: list[dict[str, Any]] = []

    if isro_scan.get("status") == "scanned":
        missing = [key for key in REQUIRED_MARKERS if not marker_present(isro_scan["markers"][key])]
        checks.append(
            check_item(
                "isro_reference_required_markers",
                "pass" if not missing else "fail",
                "ISRO GS reference contains required return markers"
                if not missing
                else f"ISRO GS reference is missing markers: {', '.join(missing)}",
            )
        )
    else:
        checks.append(check_item("isro_reference_required_markers", "fail", "ISRO GS reference file is missing"))

    if csro_scan.get("status") == "scanned":
        missing = [key for key in REQUIRED_MARKERS if not marker_present(csro_scan["markers"][key])]
        checks.append(
            check_item(
                "csro_literal_markers_present",
                "pass" if not missing else "fail",
                "CSRO GS contains literal return markers; this is not proof of active routing"
                if not missing
                else f"CSRO GS is missing literal markers: {', '.join(missing)}",
                severity="informational",
            )
        )
        refskilv_count = marker_counts(csro_scan, "_REFSKILV")
        checks.append(
            check_item(
                "gs_refskilv_user_patch_preserved",
                "pass" if refskilv_count > 0 else "fail",
                f"_REFSKILV occurrence count: {refskilv_count}; this must be preserved",
            )
        )
    else:
        checks.append(check_item("csro_literal_markers_present", "fail", "CSRO live GS file is missing"))
        checks.append(check_item("gs_refskilv_user_patch_preserved", "fail", "CSRO live GS file is missing"))

    active_slot = read_u32(csro_path, ACTIVE_FILTER_SLOT_RAW)
    if active_slot is None:
        checks.append(check_item("gs_active_filter_slot_readable", "fail", "active filter slot is not readable"))
    else:
        checks.append(
            check_item(
                "gs_active_filter_slot_readable",
                "pass",
                f"raw 0x{ACTIVE_FILTER_SLOT_RAW:X} / VA 0x{ACTIVE_FILTER_SLOT_VA:08X} = 0x{active_slot:08X}",
                severity="informational",
            )
        )
        checks.append(
            check_item(
                "old_csro_filter_still_active",
                "pass" if active_slot == EXPECTED_OLD_CSRO_FILTER else "fail",
                f"active filter is 0x{active_slot:08X}; expected old CSRO filter 0x{EXPECTED_OLD_CSRO_FILTER:08X}",
            )
        )
        if active_slot == EXPECTED_OLD_CSRO_FILTER:
            detail = (
                "new return GS branch is still not active: active slot points to old CSRO filter "
                f"0x{EXPECTED_OLD_CSRO_FILTER:08X}, not a reviewed 0xCC/0xCF return handler"
            )
            status = "fail"
        elif active_slot == KNOWN_FAILED_NEW_FILTER:
            detail = (
                f"active slot points to known historical new handler 0x{KNOWN_FAILED_NEW_FILTER:08X}; "
                "this is not sufficient without current ISRO/CSRO proof"
            )
            status = "fail"
        else:
            detail = f"active slot is 0x{active_slot:08X}; no reviewed evidence maps this to the new return branch"
            status = "fail"
        checks.append(check_item("new_return_gs_branch_active", status, detail))

    required_failures = [item for item in checks if item["severity"] == "required" and item["status"] == "fail"]
    status = "blocked" if required_failures else "aligned"
    return {
        "round": ROUND,
        "tool": Path(__file__).name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only",
        "status": status,
        "files": {
            "isro_reference_gs": file_info(isro_path),
            "csro_live_gs": file_info(csro_path),
        },
        "active_filter_slot": {
            "raw_offset": f"0x{ACTIVE_FILTER_SLOT_RAW:X}",
            "va": f"0x{ACTIVE_FILTER_SLOT_VA:08X}",
            "value": None if active_slot is None else f"0x{active_slot:08X}",
            "expected_old_csro_filter": f"0x{EXPECTED_OLD_CSRO_FILTER:08X}",
            "known_failed_new_filter": f"0x{KNOWN_FAILED_NEW_FILTER:08X}",
        },
        "checks": checks,
        "marker_counts": {
            "isro_reference_gs": {
                key: marker_counts(isro_scan, key) for key in (*REQUIRED_MARKERS, "_REFSKILV", "_REFSKILL")
            },
            "csro_live_gs": {
                key: marker_counts(csro_scan, key) for key in (*REQUIRED_MARKERS, "_REFSKILV", "_REFSKILL")
            },
        },
        "conclusion": (
            "CSRO live GS preserves _REFSKILV and old CSRO active filter, but the reviewed new 0xCC/0xCF "
            "GS branch is not active/proven. Do not write a GS patch until a patch spec identifies exact "
            "VA/raw offsets, old/new bytes, and ISRO-to-CSRO evidence."
        ),
    }


def print_text(payload: dict[str, Any]) -> None:
    print(f"{payload['tool']}: {payload['status']}")
    print(payload["conclusion"])
    print()
    for item in payload["checks"]:
        print(f"[{item['status']}] {item['name']} ({item['severity']}) - {item['detail']}")


def emit_json(payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only CSRO GS return-path alignment check.")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument("--isro-gs", default=str(DEFAULT_ISRO_GS), help="ISRO GS reference path")
    parser.add_argument("--csro-gs", default=str(DEFAULT_CSRO_GS), help="CSRO live GS path")
    parser.add_argument("--max-occurrences", type=int, default=5, help="shown scan occurrences per pattern")
    args = parser.parse_args()

    payload = build_payload(args)
    if args.json:
        emit_json(payload)
    else:
        print_text(payload)
    return 0 if payload["status"] == "aligned" else 1


if __name__ == "__main__":
    sys.exit(main())
