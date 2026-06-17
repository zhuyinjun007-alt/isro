from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import post_reverse_return_issue_comment as issue_comment


class IssueCommentBodyTest(unittest.TestCase):
    def test_body_links_reports_tools_and_blocked_status(self) -> None:
        body = issue_comment.build_body(2, issue_comment.ROUND, "abc123")

        required = [
            "[规格文档](https://github.com/zhuyinjun007-alt/isro/blob/abc123/docs/superpowers/specs/2026-06-17-isro-new-return-actions-design.md)",
            "[实施计划](https://github.com/zhuyinjun007-alt/isro/blob/abc123/docs/superpowers/plans/2026-06-17-isro-new-return-actions.md)",
            "[Task 6 验收模板/待验证清单](https://github.com/zhuyinjun007-alt/isro/blob/abc123/reports/2026-06-17-phase-isro-new-return-actions-task6-smoke.md)",
            "[客户端 handler 门禁脚本](https://github.com/zhuyinjun007-alt/isro/blob/abc123/tools/apply_client_new_return_handlers.py)",
            "[GS patch 门禁脚本](https://github.com/zhuyinjun007-alt/isro/blob/abc123/tools/apply_gs_return_action_patch.py)",
            "[源码工具目录](https://github.com/zhuyinjun007-alt/isro/tree/abc123/tools)",
            "[阶段报告目录](https://github.com/zhuyinjun007-alt/isro/tree/abc123/reports)",
            "[证据目录](https://github.com/zhuyinjun007-alt/isro/tree/abc123/evidence)",
            "[本次提交](https://github.com/zhuyinjun007-alt/isro/commit/abc123)",
            "当前结论：部分完成，写入门禁仍阻塞",
            "游戏内冒烟仍未完成",
            "运行时 `0x21` trace",
        ]

        for expected in required:
            with self.subTest(expected=expected):
                self.assertIn(expected, body)


if __name__ == "__main__":
    unittest.main()
