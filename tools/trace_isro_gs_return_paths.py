from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROUND = "phase-isro-new-return-actions-20260617"
DEFAULT_ISRO_GS = Path(r"F:\SR_GameServer.exe")
DEFAULT_CSRO_GS = Path(r"D:\CSRO\8-SR_GameServer.exe")

NUMERIC_MARKERS: tuple[tuple[str, int, str], ...] = (
    ("0x3213", 0x3213, "队员位置传送请求 marker"),
    ("0x705A", 0x705A, "使用者指定位置传送请求 marker"),
    ("0x759F", 0x759F, "队员位置列表请求 marker"),
    ("0x7600", 0x7600, "保存位置列表请求 marker"),
    ("0xB59F", 0xB59F, "队员位置列表响应 marker"),
    ("0xB600", 0xB600, "保存位置列表响应 marker"),
    ("9114", 9114, "返回物品白名单 item id marker"),
    ("24298", 24298, "返回物品白名单 item id marker"),
)

STRING_MARKERS: tuple[tuple[str, bytes, str], ...] = (
    ("_REFSKILV", b"_REFSKILV", "用户独立补丁保留项"),
    ("_REFSKILL", b"_REFSKILL", "原始字符串/相邻参考"),
)


@dataclass(frozen=True)
class Section:
    name: str
    rva: int
    virtual_size: int
    raw: int
    raw_size: int


@dataclass(frozen=True)
class PeImage:
    image_base: int
    sections: tuple[Section, ...]

    def raw_to_va(self, raw: int) -> int | None:
        for section in self.sections:
            if section.raw <= raw < section.raw + section.raw_size:
                return self.image_base + section.rva + (raw - section.raw)
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def file_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if path.exists():
        stat = path.stat()
        info.update(
            {
                "sha256": sha256_file(path),
                "length": stat.st_size,
                "last_write_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            }
        )
    return info


def load_pe(data: bytes) -> PeImage | None:
    if len(data) < 0x40 or data[:2] != b"MZ":
        return None
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_off + 0x18 >= len(data) or data[pe_off : pe_off + 4] != b"PE\0\0":
        return None
    coff = pe_off + 4
    section_count = struct.unpack_from("<H", data, coff + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x10B:
        image_base = struct.unpack_from("<I", data, opt + 28)[0]
    elif magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, opt + 24)[0]
    else:
        return None

    sections: list[Section] = []
    section_table = opt + optional_size
    for index in range(section_count):
        off = section_table + index * 40
        if off + 40 > len(data):
            break
        name = data[off : off + 8].split(b"\0", 1)[0].decode("ascii", errors="replace")
        virtual_size, rva, raw_size, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append(Section(name, rva, virtual_size, raw, raw_size))
    return PeImage(image_base, tuple(sections))


def find_all(data: bytes, needle: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return offsets
        offsets.append(pos)
        start = pos + 1


def hex_bytes(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def occurrence(raw: int, data: bytes, pe: PeImage | None, context: int) -> dict[str, Any]:
    start = max(0, raw - context)
    end = min(len(data), raw + context)
    va = pe.raw_to_va(raw) if pe else None
    item: dict[str, Any] = {
        "raw_offset": f"0x{raw:X}",
        "context_hex": hex_bytes(data[start:end]),
    }
    if va is not None:
        item["va"] = f"0x{va:08X}"
    return item


def scan_pattern(
    data: bytes,
    pe: PeImage | None,
    pattern: bytes,
    *,
    max_occurrences: int,
    include_all: bool,
    context: int,
) -> dict[str, Any]:
    offsets = find_all(data, pattern)
    selected = offsets if include_all else offsets[:max_occurrences]
    return {
        "pattern_hex": hex_bytes(pattern),
        "count": len(offsets),
        "shown": len(selected),
        "truncated": len(selected) < len(offsets),
        "occurrences": [occurrence(raw, data, pe, context) for raw in selected],
    }


def scan_file(path: Path, *, max_occurrences: int = 12, include_all: bool = False, context: int = 12) -> dict[str, Any]:
    if not path.exists():
        return {"file": file_info(path), "status": "missing_file", "markers": {}}
    data = path.read_bytes()
    pe = load_pe(data)
    markers: dict[str, Any] = {}

    for key, value, description in NUMERIC_MARKERS:
        patterns = {
            "le16": scan_pattern(
                data,
                pe,
                value.to_bytes(2, "little"),
                max_occurrences=max_occurrences,
                include_all=include_all,
                context=context,
            ),
            "le32": scan_pattern(
                data,
                pe,
                value.to_bytes(4, "little"),
                max_occurrences=max_occurrences,
                include_all=include_all,
                context=context,
            ),
        }
        markers[key] = {"kind": "numeric", "description": description, "value": value, "patterns": patterns}

    for key, pattern, description in STRING_MARKERS:
        markers[key] = {
            "kind": "string",
            "description": description,
            "patterns": {
                "ascii": scan_pattern(
                    data,
                    pe,
                    pattern,
                    max_occurrences=max_occurrences,
                    include_all=include_all,
                    context=context,
                )
            },
        }

    pe_payload: dict[str, Any] | None = None
    if pe:
        pe_payload = {
            "image_base": f"0x{pe.image_base:08X}",
            "sections": [
                {
                    "name": s.name,
                    "rva": f"0x{s.rva:X}",
                    "raw": f"0x{s.raw:X}",
                    "virtual_size": f"0x{s.virtual_size:X}",
                    "raw_size": f"0x{s.raw_size:X}",
                }
                for s in pe.sections
            ],
        }

    return {"file": file_info(path), "status": "scanned", "pe": pe_payload, "markers": markers}


def marker_present(marker_payload: dict[str, Any]) -> bool:
    return any(pattern["count"] > 0 for pattern in marker_payload["patterns"].values())


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    targets: list[tuple[str, Path]] = []
    if args.target in ("both", "isro"):
        targets.append(("isro_reference_gs", Path(args.isro_gs)))
    if args.target in ("both", "csro"):
        targets.append(("csro_live_gs", Path(args.csro_gs)))

    scans = {
        name: scan_file(path, max_occurrences=args.max_occurrences, include_all=args.all, context=args.context)
        for name, path in targets
    }

    summaries: dict[str, Any] = {}
    for name, scan in scans.items():
        if scan.get("status") != "scanned":
            summaries[name] = {"status": scan.get("status")}
            continue
        summaries[name] = {
            key: marker_present(marker)
            for key, marker in scan["markers"].items()
        }

    interpretation = [
        "This is a raw marker scan only; it does not prove control-flow reachability or runtime behavior.",
        "The current standard ISRO GS reference is F:\\SR_GameServer.exe.",
        "For CSRO live GS, _REFSKILV must be preserved and must not be treated as return-chain pollution.",
    ]
    if "csro_live_gs" in summaries:
        csro_summary = summaries["csro_live_gs"]
        if csro_summary.get("_REFSKILV"):
            interpretation.append("CSRO live GS contains _REFSKILV; this matches the Phase11 preservation rule.")
        else:
            interpretation.append("CSRO live GS does not show _REFSKILV in this scan; check whether the target path/hash is current.")

    return {
        "round": ROUND,
        "tool": Path(__file__).name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only",
        "scans": scans,
        "summary": summaries,
        "interpretation": interpretation,
    }


def print_text(payload: dict[str, Any]) -> None:
    print(f"{payload['tool']} ({payload['mode']})")
    print(f"round: {payload['round']}")
    for name, scan in payload["scans"].items():
        info = scan["file"]
        print()
        print(f"[{name}] {info['path']}")
        if scan.get("status") != "scanned":
            print(f"  status: {scan.get('status')}")
            continue
        print(f"  sha256: {info['sha256']}")
        print(f"  length: {info['length']}")
        for key, marker in scan["markers"].items():
            pieces = []
            for pattern_name, pattern in marker["patterns"].items():
                first = pattern["occurrences"][0]["raw_offset"] if pattern["occurrences"] else "-"
                pieces.append(f"{pattern_name}=count:{pattern['count']},first:{first}")
            print(f"  {key:<10} {'; '.join(pieces)}")
    print()
    print("interpretation:")
    for line in payload["interpretation"]:
        print(f"  - {line}")


def emit_json(payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only marker scan for ISRO/CSRO GS return paths."
    )
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument("--target", choices=("both", "isro", "csro"), default="both")
    parser.add_argument("--isro-gs", default=str(DEFAULT_ISRO_GS), help="ISRO GS reference path")
    parser.add_argument("--csro-gs", default=str(DEFAULT_CSRO_GS), help="CSRO live GS path")
    parser.add_argument("--max-occurrences", type=int, default=12, help="shown occurrences per pattern")
    parser.add_argument("--all", action="store_true", help="show every occurrence")
    parser.add_argument("--context", type=int, default=12, help="context bytes around each occurrence")
    args = parser.parse_args()

    if args.max_occurrences < 0:
        parser.error("--max-occurrences must be non-negative")
    if args.context < 0:
        parser.error("--context must be non-negative")

    payload = build_payload(args)
    if args.json:
        emit_json(payload)
    else:
        print_text(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
