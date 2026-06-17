# Phase9 - F盘 ISRO GS 参考源冻结记录

记录时间：2026-06-16

## 本轮结论

- 本轮 ISRO GS 唯一标准参考源：`F:\SR_GameServer.exe`
- 禁止继续把 `G:\SR_GameServer.exe`、`samples/raw/isro_gs.exe`、历史摘要里的 hash 当作本轮标准。
- `samples/raw/isro_gs.exe` 只能做历史差异对比，不再作为修复依据。
- 本轮尚未写入 `F:\CSRO客户端\SRO_Client.exe` 或 `D:\CSRO\8-SR_GameServer.exe`。

## 当前冻结 hash

| 文件 | SHA256 | 时间 | 大小 |
| --- | --- | --- | --- |
| `F:\SR_GameServer.exe` | `6491737E65454C577CE72384C30DBEC72E57F9B8ECD064D8B4D1ABB42D8EC302` | `2025-02-02 05:47:54` | `12218368` |
| `F:\ISRO客户端国服\sro_client.exe` | `5AAE7E89985FEAFC4BB4273CAF73FB338213771C3488C756013B65182170ECB0` | `2026-06-11 19:15:50` | `14196736` |
| `F:\CSRO客户端\SRO_Client.exe` | `182710ABFF4532657508D213F4620DE4ABF583DBB7D493E1F791AA915CD01F46` | `2026-06-16 17:33:44` | `13066240` |
| `D:\CSRO\8-SR_GameServer.exe` | `D89E128FECD1BE9FE2E0D67102A407213CFDF9547D65845092BBAAB0EB57373A` | `2026-06-16 06:51:01` | `9949184` |

证据文件：

- `C:\Users\43584\Documents\添加ISRO的返回功能\evidence\freeze-reverse-return-phase9-reference-20260616-rerun.json`

## 新旧 ISRO GS 差异

`F:\SR_GameServer.exe` 与 `samples/raw/isro_gs.exe`：

- hash 不同。
- 文件大小相同：`12218368`。
- 重叠范围差异字节数：`1703`。
- 典型差异包含多处 `68 01 00 00 02` 与 `6A 00 90 90 90` 的差异。

结论：旧 `samples/raw/isro_gs.exe` 不是本轮标准源，后续所有 GS 链路提取必须重新以 `F:\SR_GameServer.exe` 为准。

## 新参考 GS 中已确认的返回链路 marker

`F:\SR_GameServer.exe` 中可见：

- `0x3213`
- `0x705A`
- `0x759F`
- `0x7600`
- `0xB59F`
- `0xB600`
- 组队人数门槛 marker：`83 7F 1C 02`

这只能证明参考 GS 中存在相关 marker，不能直接证明 CSRO 已完整修复。

## 当前 CSRO 状态判定

当前 live EXE 仍在失败态，不能继续按成功态推进：

- `check_reverse_return_phase8_base_chain_extension.py`：`4 pass / 6 fail`
- 失败核心：`0x00EBE9F8 -> 0x12ED000`，仍是整表 message-map entries 替换。
- `0x12ED000` 当前仍被解析为整张 entries，不是小扩展 header。
- `check_reverse_return_exact_isro_compare.py`：`4 pass / 4 fail`
- 失败核心：当前动态右键路径仍到 `0x12EC930`，不是旧记录期望的 guard cave；旧的 guard/lifecycle 路线不能再当成功标准。
- `deep_reverse_chain_check.py`：`11 pass / 0 fail`，但这只是静态链路存在，不能作为游戏内成功证据。

## 后续禁止路线

- 禁止用旧 `samples/raw/isro_gs.exe` 继续做 GS 标准。
- 禁止引用历史摘要中的 `E3B6...`、`165552...`、`699348...` 作为当前现场 hash。
- 禁止继续整表替换 message-map / entries。
- 禁止把旧按钮 `0xC8/0xC9/0xCA/0xCB` 改到新 handler。
- 禁止把静态 marker 通过当作游戏内成功。
- 禁止再执行 EXE-only 修复并宣称 GS/EXE 同轮闭合。

## 下一轮写入前硬门槛

1. 同时备份 `F:\CSRO客户端\SRO_Client.exe` 和 `D:\CSRO\8-SR_GameServer.exe`。
2. manifest 记录写前 hash、写后 hash、LastWriteTime、VA、raw offset、bytes。
3. 只允许保留旧 CSRO 按钮原链路，只新增 `0xCC/0xCF`。
4. GS/EXE 必须都以 `F:\SR_GameServer.exe` 与 `F:\ISRO客户端国服\sro_client.exe` 为参考重新对照。
5. 失败后直接恢复本轮备份 EXE 和 GS，不再叠补丁。
