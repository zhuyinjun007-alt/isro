from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROUND = "phase-isro-new-return-actions-20260617"
REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "evidence"
REPORTS_DIR = REPO_ROOT / "reports"
BACKUP_ROOT = Path.home() / "Documents" / "添加ISRO的返回功能" / "backups"

CSRO_EXE = Path(r"F:\CSRO客户端\SRO_Client.exe")
CSRO_GS = Path(r"D:\CSRO\8-SR_GameServer.exe")
ISRO_EXE = Path(r"F:\ISRO客户端国服\sro_client.exe")
ISRO_GS = Path(r"F:\SR_GameServer.exe")

EXPECTED_CURRENT = {
    str(CSRO_EXE): "280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E",
    str(CSRO_GS): "B5C56F6A92B317C1701E1CF9E963754E4A0A52FFA74ACEFD91BC1E1DF8915C98",
}


class EvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Section:
    name: str
    va: int
    virtual_size: int
    raw: int
    raw_size: int


@dataclass(frozen=True)
class PeImage:
    path: Path
    image_base: int
    sections: tuple[Section, ...]

    def va_to_raw(self, va: int) -> int:
        rva = va - self.image_base
        if rva < 0:
            raise EvidenceError(f"VA 0x{va:08X} is below image base 0x{self.image_base:08X}")
        for section in self.sections:
            size = max(section.virtual_size, section.raw_size)
            if section.va <= rva < section.va + size:
                return section.raw + (rva - section.va)
        raise EvidenceError(f"VA 0x{va:08X} is not mapped by PE sections")

    def raw_to_va(self, raw: int) -> int:
        for section in self.sections:
            if section.raw <= raw < section.raw + section.raw_size:
                return self.image_base + section.va + (raw - section.raw)
        raise EvidenceError(f"raw 0x{raw:08X} is not mapped by PE sections")


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def file_info(path: Path) -> dict[str, Any]:
    exists = path.exists()
    info: dict[str, Any] = {"path": str(path), "exists": exists}
    if exists:
        stat = path.stat()
        info.update(
            {
                "sha256": sha256_file(path),
                "length": stat.st_size,
                "last_write_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            }
        )
    return info


def load_pe(path: Path) -> PeImage:
    data = read_bytes(path)
    if data[:2] != b"MZ":
        raise EvidenceError(f"{path} is not a PE file")
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_off : pe_off + 4] != b"PE\0\0":
        raise EvidenceError(f"{path} has no PE signature")
    coff = pe_off + 4
    number_of_sections = struct.unpack_from("<H", data, coff + 2)[0]
    optional_header_size = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x10B:
        image_base = struct.unpack_from("<I", data, opt + 28)[0]
    elif magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, opt + 24)[0]
    else:
        raise EvidenceError(f"{path} has unsupported optional header magic 0x{magic:X}")

    sections: list[Section] = []
    section_table = opt + optional_header_size
    for index in range(number_of_sections):
        off = section_table + index * 40
        raw_name = data[off : off + 8].split(b"\0", 1)[0]
        name = raw_name.decode("ascii", errors="replace")
        virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
        sections.append(Section(name, virtual_address, virtual_size, raw_ptr, raw_size))
    return PeImage(path, image_base, tuple(sections))


def hex_bytes(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def parse_hex_bytes(value: str) -> bytes:
    compact = value.replace(" ", "").replace("-", "").replace("_", "")
    if len(compact) % 2:
        raise argparse.ArgumentTypeError(f"invalid hex byte string: {value}")
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def find_all(data: bytes, needle: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            return offsets
        offsets.append(pos)
        start = pos + 1


def read_at(path: Path, raw: int, length: int) -> bytes:
    with path.open("rb") as f:
        f.seek(raw)
        return f.read(length)


def require_current_hash(path: Path) -> None:
    expected = EXPECTED_CURRENT.get(str(path))
    if not expected:
        return
    actual = sha256_file(path)
    if actual != expected:
        raise EvidenceError(f"{path} hash mismatch: expected {expected}, actual {actual}")


def backup_dir(round_name: str = ROUND) -> Path:
    return BACKUP_ROOT / round_name


def ensure_round_backup(round_name: str = ROUND) -> Path:
    target = backup_dir(round_name)
    target.mkdir(parents=True, exist_ok=True)
    for src, name in ((CSRO_EXE, "SRO_Client.exe"), (CSRO_GS, "8-SR_GameServer.exe")):
        if not src.exists():
            raise EvidenceError(f"missing live file: {src}")
        dst = target / name
        if not dst.exists():
            shutil.copy2(src, dst)
    return target


def load_manifest(round_name: str = ROUND) -> dict[str, Any]:
    manifest_path = EVIDENCE_DIR / "2026-06-17-phase-isro-new-return-actions-manifest.json"
    if not manifest_path.exists():
        raise EvidenceError(f"missing manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_commit_url(commit: str) -> str:
    return f"https://github.com/zhuyinjun007-alt/isro/commit/{commit}"


def github_blob_url(commit: str, path: str) -> str:
    return f"https://github.com/zhuyinjun007-alt/isro/blob/{commit}/{path.replace(os.sep, '/')}"


def github_tree_url(commit: str, path: str) -> str:
    return f"https://github.com/zhuyinjun007-alt/isro/tree/{commit}/{path.replace(os.sep, '/')}"


def run_git(args: Iterable[str]) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def fail(message: str, *, json_mode: bool = False, extra: dict[str, Any] | None = None) -> int:
    payload = {"status": "blocked", "reason": message}
    if extra:
        payload.update(extra)
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"BLOCKED: {message}", file=sys.stderr)
    return 2


def add_json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


def print_payload(payload: Any, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if isinstance(payload, str):
            print(payload)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
