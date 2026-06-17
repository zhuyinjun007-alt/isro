# Task 2：客户端入口与旧按钮链路

轮次：`phase-isro-new-return-actions-20260617`

## 结论

已完成静态/历史证据复核：当前证据仍指向右键入口 `0x21`，`0xC8/0xC9/0xCA/0xCB` 没有落入新 handler，当前 active message-map 仍保持旧 CSRO 链路。
阻塞项是运行时动态证据未在本轮重新采集，不能把静态结论写成 live 最终结论。

## 已完成

- 已完成：`check_reverse_return_phase10_ui_only_restore.py --json`
  - 结果：`DONE`
  - 关键结论：`0x00EC21B4 / 0x00FFE1E8` 仍是 active base/entries。
- 已完成：`trace_reverse_return_message_map.py --json`
  - 结果：`DONE`
  - 关键结论：未复用已失败的 `0x012ED000` 整表替换路线。
- 已完成：`find_reverse_return_entry.py --json`
  - 结果：`DONE_WITH_CONCERNS`
  - 关键结论：历史证据与旧报告一致，真实入口是 `SetMsgBoxHandler arg0=0x21`。

## 阻塞

- 阻塞：本轮没有重新下运行时断点或游戏内复测，`0x21` 入口仍缺动态复验。
- 阻塞：旧按钮链路虽然静态保持，但还没补齐本轮运行时截图/日志。

## 待补证据

- 待补证据：运行时 `0x21` 入口 trace。
- 待补证据：第一次/第二次右键的现场记录。
- 待补证据：旧按钮 `0xC8/0xC9/0xCA/0xCB` 的游戏内稳定性记录。

## 验证命令和结果

- `python .\\tools\\check_reverse_return_phase10_ui_only_restore.py --json`
  - 结果：`DONE`
- `python .\\tools\\trace_reverse_return_message_map.py --json`
  - 结果：`DONE`
- `python .\\tools\\find_reverse_return_entry.py --json`
  - 结果：`DONE_WITH_CONCERNS`
