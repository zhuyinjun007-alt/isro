from __future__ import annotations

import argparse
import shutil
import sys

from isro_return_common import CSRO_EXE, CSRO_GS, ROUND, backup_dir, file_info, print_payload, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore EXE/GS from a round backup.")
    parser.add_argument("--round", default=ROUND, help="round name")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument("--execute", action="store_true", help="actually restore files")
    args = parser.parse_args()

    bdir = backup_dir(args.round)
    exe_backup = bdir / "SRO_Client.exe"
    gs_backup = bdir / "8-SR_GameServer.exe"
    checks = {
        "backup_dir": str(bdir),
        "exe_backup": file_info(exe_backup),
        "gs_backup": file_info(gs_backup),
        "live_exe_before": file_info(CSRO_EXE),
        "live_gs_before": file_info(CSRO_GS),
        "executed": args.execute,
    }
    if not exe_backup.exists() or not gs_backup.exists():
        checks["status"] = "blocked"
        checks["reason"] = "round backup is incomplete"
        print_payload(checks, args.json)
        return 2

    if args.execute:
        shutil.copy2(exe_backup, CSRO_EXE)
        shutil.copy2(gs_backup, CSRO_GS)
        checks["live_exe_after"] = file_info(CSRO_EXE)
        checks["live_gs_after"] = file_info(CSRO_GS)
        checks["restored_hashes_match_backup"] = {
            "exe": sha256_file(CSRO_EXE) == sha256_file(exe_backup),
            "gs": sha256_file(CSRO_GS) == sha256_file(gs_backup),
        }
        checks["status"] = "restored"
    else:
        checks["status"] = "dry_run"
        checks["reason"] = "pass --execute to copy backup files over live EXE/GS"

    print_payload(checks, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
