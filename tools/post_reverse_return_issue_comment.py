from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from isro_return_common import ROUND, github_blob_url, github_tree_url, git_commit_url, run_git


REPO = "zhuyinjun007-alt/isro"


def get_token() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    raise RuntimeError("no GitHub token found in GH_TOKEN/GITHUB_TOKEN or git credential fill")


def build_body(issue: int, round_name: str, commit: str) -> str:
    links = {
        "规格文档": github_blob_url(commit, "docs/superpowers/specs/2026-06-17-isro-new-return-actions-design.md"),
        "实施计划": github_blob_url(commit, "docs/superpowers/plans/2026-06-17-isro-new-return-actions.md"),
        "Task 1 冻结报告": github_blob_url(commit, "reports/2026-06-17-phase-isro-new-return-actions-task1-freeze.md"),
        "Task 6 验收模板/待验证清单": github_blob_url(commit, "reports/2026-06-17-phase-isro-new-return-actions-task6-smoke.md"),
        "客户端 handler 门禁脚本": github_blob_url(commit, "tools/apply_client_new_return_handlers.py"),
        "GS patch 门禁脚本": github_blob_url(commit, "tools/apply_gs_return_action_patch.py"),
        "manifest": github_blob_url(commit, "evidence/2026-06-17-phase-isro-new-return-actions-manifest.json"),
        "源码工具目录": github_tree_url(commit, "tools"),
        "阶段报告目录": github_tree_url(commit, "reports"),
        "证据目录": github_tree_url(commit, "evidence"),
        "本次提交": git_commit_url(commit),
    }
    lines = [
        f"本轮 `{round_name}` 已执行到门禁收口，但仍有写入阻塞，当前不能把 GS 写入当作完成。",
        "",
        "当前结论：部分完成，写入门禁仍阻塞。",
        "",
        "当前状态：",
        "",
        "- 客户端侧脚本、GS 只读扫描和门禁脚本已落地。",
        "- 现有报告明确了静态证据、阻塞缺口和保留项。",
        "- 游戏内冒烟仍未完成，`smoke.json` 仍是 `manual_smoke_required`。",
        "- 还缺可复核的 0xCC/0xCF 写入计划和运行时闭环，因此不能直接写 live GS。",
        "- `_REFSKILV` 仍需保留，旧 CSRO 按钮链路也必须继续保留。",
        "",
        "仍缺证据：",
        "",
        "- 运行时 `0x21` trace。",
        "- 第一次/第二次右键现场验证。",
        "- `0xCC` 单人置灰与 2 人组队可用现场验证。",
        "- `0xCC/0xCF` runtime dispatch 与发包证据。",
        "- 客户端 old/new bytes 写入计划与 GS reviewed patch spec。",
        "",
        "可点击链接：",
        "",
    ]
    for title, url in links.items():
        lines.append(f"- [{title}]({url})")
    lines.append("")
    lines.append(f"Issue: #{issue}")
    return "\n".join(lines)


def post_comment(issue: int, body: str, token: str) -> dict:
    data = json.dumps({"body": body}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues/{issue}/comments",
        data=data,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "codex-isro-return",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Post UTF-8 GitHub issue comment for this round.")
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--round", default=ROUND)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    commit = run_git(["rev-parse", "HEAD"])
    body = args.body_file.read_text(encoding="utf-8") if args.body_file else build_body(args.issue, args.round, commit)
    if args.dry_run:
        print(body)
        return 0

    token = get_token()
    result = post_comment(args.issue, body, token)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result.get("html_url", "comment posted"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
