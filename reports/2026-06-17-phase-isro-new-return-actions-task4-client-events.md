# Task 4：客户端事件与新 handler

轮次：`phase-isro-new-return-actions-20260617`

## 结论

已完成静态 handler / 协议线索采集：`0xCC` 与 `0xCF` 的候选 handler 和相关 opcode 都能在当前/参考客户端里被静态扫到。
阻塞项是 active dispatch 没闭合、运行时发包没抓到，所以 `apply_client_new_return_handlers.py` 按门禁正确拒绝写入。

## 已完成

- 已完成：`trace_reverse_return_new_handlers.py --json`
  - 结果：`DONE_WITH_CONCERNS`
  - 关键结论：静态候选可见，`0xCC -> 0x012DEF50`，`0xCF -> 0x012DF020`。
- 已完成：`trace_reverse_return_packets.py --json`
  - 结果：`DONE_WITH_CONCERNS`
  - 关键结论：当前客户端和 ISRO 参考客户端里都能静态扫到 `0x759F / 0x7600 / 0xB59F / 0xB600 / 0x3213 / 0x705A` 相关线索。
- 已运行门禁：`apply_client_new_return_handlers.py --json`
  - 结果：`BLOCKED`
  - 关键结论：缺少可复核的写入计划与运行时证据，脚本主动拒绝写入。

## 阻塞

- 阻塞：没有 active dispatch 闭合证据，不能把静态候选当成已接入。
- 阻塞：没有抓包或 hook 发送函数，不能证明点击 `0xCC/0xCF` 已发出正确请求。
- 阻塞：没有形成可写入的 VA/raw offset/old bytes/new bytes 完整计划。

## 待补证据

- 待补证据：`0xCC/0xCF` 的 runtime dispatch。
- 待补证据：实际点击后的发包链路。
- 待补证据：若要写入，需补齐逐字节 old/new 计划和回滚点。

## 验证命令和结果

- `python .\\tools\\trace_reverse_return_new_handlers.py --json`
  - 结果：`DONE_WITH_CONCERNS`
- `python .\\tools\\trace_reverse_return_packets.py --json`
  - 结果：`DONE_WITH_CONCERNS`
- `python .\\tools\\apply_client_new_return_handlers.py --json`
  - 结果：`BLOCKED`
