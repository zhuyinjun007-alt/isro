# Task 3：客户端队员按钮 gate

轮次：`phase-isro-new-return-actions-20260617`

## 结论

已完成静态 gate 字节复核：`0xCC` 队员按钮 call site 当前指向专用 gate，字节已对应 `state_global+0x44 > 0`，没有复用 Phase11A 失败的 `state_global+0x30 >= 2` 路线。
阻塞项仍然是游戏内单人置灰与 2 人组队可用性没有在本轮重新验证。

## 已完成

- 已完成：`check_reverse_return_party_gate.py --json`
  - 结果：`DONE_WITH_CONCERNS`
  - 关键结论：`0x012E3BC6 -> 0x012EC9C0`，gate 字节为 `83 79 44 00 0F 97 C0 C3`。
- 已完成：`check_reverse_return_phase11_party_enable_gate.py --json`
  - 结果：`DONE`
  - 关键结论：当前客户端仍是 Phase2 冻结态，未回到 `state_global+0x30` 失败路线。
- 已完成：`trace_team_member_enable_source.py --json`
  - 结果：`DONE_WITH_CONCERNS`
  - 关键结论：gate 来源与 Phase2 报告一致，来源是队员列表计数。
- 已完成：`apply_client_party_enable_patch.py --json`
  - 结果：`DONE_WITH_CONCERNS`
  - 关键结论：目标已经是期望 gate 字节，本轮没有重复写入。

## 阻塞

- 阻塞：没有游戏内复测单人状态下的置灰表现。
- 阻塞：没有复测 2 人及以上组队时的可用状态。

## 待补证据

- 待补证据：单人未组队时 `0xCC` 灰色不可选。
- 待补证据：2 人及以上组队时 `0xCC` 可选。
- 待补证据：旧 CSRO 返回功能在本轮环境中的现场回归。

## 验证命令和结果

- `python .\\tools\\check_reverse_return_party_gate.py --json`
  - 结果：`DONE_WITH_CONCERNS`
- `python .\\tools\\check_reverse_return_phase11_party_enable_gate.py --json`
  - 结果：`DONE`
- `python .\\tools\\trace_team_member_enable_source.py --json`
  - 结果：`DONE_WITH_CONCERNS`
- `python .\\tools\\apply_client_party_enable_patch.py --json`
  - 结果：`DONE_WITH_CONCERNS`
