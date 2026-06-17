# Task 6：端到端验收、回滚与 issue 回复

轮次：`phase-isro-new-return-actions-20260617`

## 当前状态

本报告目前是验收记录模板。已生成冒烟验收 JSON 模板，但尚未完成游戏内人工验证，也未执行 GitHub issue 正式回复。

## 验收清单

| 项目 | 状态 | 证据 |
| --- | --- | --- |
| 第一次右键返回卷轴 UI 正常出现 | 待验证 | 需游戏内复现 |
| 关闭后第二次右键返回卷轴 UI 正常出现 | 待验证 | 需游戏内复现 |
| 旧 CSRO 按钮 `0xC8/0xC9/0xCA/0xCB` 功能仍可用 | 待验证 | 需游戏内复现 |
| 单人未组队时 `0xCC` 灰色不可选 | 待验证 | 需游戏内复现 |
| 两人及以上组队时 `0xCC` 可选 | 待验证 | 需游戏内复现 |
| `0xCC` 点击后不闪退并进入预期链路 | 待验证 | 需游戏内复现 |
| `0xCF` 点击后不闪退并进入预期链路 | 待验证 | 需游戏内复现 |
| 同时间段无新增客户端 dump | 待验证 | 需检查 `F:\CSRO客户端\Dump` |
| 同时间段无新增 GS FatalLog | 待验证 | 需检查 `D:\CSRO` 日志目录 |

## 已生成文件

- 冒烟验收模板/待验证清单：`evidence\2026-06-17-phase-isro-new-return-actions-smoke.json`
- 回滚工具：`tools\restore_reverse_return_round.py`
- issue 回复工具：`tools\post_reverse_return_issue_comment.py`

说明：当前 `smoke.json` 的状态仍为 `manual_smoke_required`，各项游戏内结果仍是 `pending`，不能作为验收通过证据。

## 回滚命令

dry-run：

```powershell
python .\tools\restore_reverse_return_round.py --round phase-isro-new-return-actions-20260617 --json
```

实际回滚：

```powershell
python .\tools\restore_reverse_return_round.py --round phase-isro-new-return-actions-20260617 --execute --json
```

## issue 回复

dry-run：

```powershell
python .\tools\post_reverse_return_issue_comment.py --issue 2 --round phase-isro-new-return-actions-20260617 --dry-run
```

正式回复必须在提交并推送后执行，这样 issue 中的源码与文档链接才能指向 GitHub 上可点击的提交内容。
