# Phase5 · GS 侧脚本与对齐报告

轮次：`phase-isro-new-return-actions-20260617`
日期：`2026-06-17`

## 结论

已完成 GS 侧只读扫描、默认安全失败的补丁脚本、以及当前 GS 静态对齐检查脚本。
当前状态仍然是 `BLOCKED`，原因不是脚本缺失，而是**没有可用于写入的 reviewed patch spec**，且当前 live GS 仍只证明旧 CSRO active filter，未证明新 `0xCC/0xCF` GS 分支已激活。

## 已完成

- `tools/trace_isro_gs_return_paths.py`
  - 只读扫描 ISRO/CSRO GS。
  - 覆盖 `0x3213`, `0x705A`, `0x759F`, `0x7600`, `0xB59F`, `0xB600`, `9114`, `24298`, `_REFSKILV/_REFSKILL`。
  - 输出 JSON / 文本。
- `tools/apply_gs_return_action_patch.py`
  - 默认拒绝写入。
  - 检查 manifest、备份、目标 hash。
  - 只有在存在 reviewed patch spec 且通过校验时才允许模拟/写入。
- `tools/check_reverse_return_gs_alignment.py`
  - 静态对齐检查当前 GS。
  - 明确报告新 GS 分支是否仍缺失。
  - 明确报告 `_REFSKILV` 是否保留。

## 阻塞

1. 当前没有 `approved_for_write` 的 patch spec。
2. 当前 `D:\CSRO\8-SR_GameServer.exe` 的 active filter slot 仍是 `0x004C8410`，说明旧 CSRO 路径仍在。
3. 当前 GS 扫描能看到 marker，但这只是静态存在，不代表 `0xCC/0xCF` 新分支已激活。

## 待补证据

- `target_path`
- `VA`
- `raw_offset`
- `old_bytes`
- `new_bytes`
- 为什么只控制 `移动至队员位置` / `移动至使用者指定的位置`
- 为什么不影响旧按钮 `0xC8/0xC9/0xCA/0xCB`
- 写入前备份目录
- 失败后恢复命令
- reviewed patch spec 的人工确认记录

## 运行的验证命令和结果

1. `python -m py_compile .\tools\trace_isro_gs_return_paths.py .\tools\apply_gs_return_action_patch.py .\tools\check_reverse_return_gs_alignment.py`
   - 结果：通过
2. `python .\tools\trace_isro_gs_return_paths.py --help`
   - 结果：通过
3. `python .\tools\apply_gs_return_action_patch.py --help`
   - 结果：通过
4. `python .\tools\check_reverse_return_gs_alignment.py --help`
   - 结果：通过
5. `python .\tools\trace_isro_gs_return_paths.py --json --max-occurrences 2`
   - 结果：通过，输出 ISRO/CSRO GS marker 扫描 JSON
6. `python .\tools\apply_gs_return_action_patch.py --json`
   - 结果：`BLOCKED`
   - 原因：`missing reviewed patch spec; GS reverse evidence is insufficient for binary write`
7. `python .\tools\check_reverse_return_gs_alignment.py --json`
   - 结果：`BLOCKED`
   - 关键点：`old_csro_filter_still_active = pass`
   - 关键点：`new_return_gs_branch_active = fail`
   - 关键点：`gs_refskilv_user_patch_preserved = pass`

## 关键证据摘要

- ISRO GS 参考源：`F:\SR_GameServer.exe`
- CSRO live GS：`D:\CSRO\8-SR_GameServer.exe`
- 当前 live GS hash：`B5C56F6A92B317C1701E1CF9E963754E4A0A52FFA74ACEFD91BC1E1DF8915C98`
- 当前对齐检查结论：
  - 旧 CSRO active filter 仍是 `0x004C8410`
  - 新返回 GS 分支仍未证明 active
  - `_REFSKILV` 已保留

## 改动文件

- `tools/trace_isro_gs_return_paths.py`
- `tools/apply_gs_return_action_patch.py`
- `tools/check_reverse_return_gs_alignment.py`
- `reports/2026-06-17-phase-isro-new-return-actions-task5-gs.md`

## 未解决风险

- 目前只能证明 marker 存在，不能证明 GS 运行时路由已闭合。
- 如果后续要真正写 GS，必须先补 reviewed patch spec，再让 `apply_gs_return_action_patch.py` 走可审查的写入路径。
- `_REFSKILV` 已按要求保留，后续任何 GS 检查都不能把它当污染清理。
