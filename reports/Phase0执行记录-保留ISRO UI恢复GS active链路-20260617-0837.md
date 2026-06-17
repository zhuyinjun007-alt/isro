# Phase0 执行记录：保留 ISRO 返回 UI，恢复/确认 GS active 返回链路

记录时间：2026-06-17 08:37

## 本轮目标

- 第 0 步只处理返回相关 active 链路，不把客户端 UI 回滚成旧 CSRO 三按钮界面。
- 必须保留 `F:\CSRO客户端\SRO_Client.exe` 中已经出现的 ISRO 风格五按钮返回 UI。
- 必须保留用户独立补丁 `_REFSKILV`，禁止清理为 `_REFSKILL`。
- 禁止整文件覆盖 `D:\CSRO\8-SR_GameServer.exe`。

## 备份

备份目录：

`C:\Users\43584\Documents\添加ISRO的返回功能\backups\pre-phase0-keep-isro-ui-restore-gs-active-20260617-083733`

备份 manifest：

`C:\Users\43584\Documents\添加ISRO的返回功能\evidence\phase0-backup-keep-isro-ui-20260617-083733.json`

写前 hash：

| 目标 | SHA256 |
| --- | --- |
| EXE | `BE9D5D0D62CC931F71B80ACEC88FBB2F297B78BF6C712A57D4A80E286615119C` |
| GS | `B5C56F6A92B317C1701E1CF9E963754E4A0A52FFA74ACEFD91BC1E1DF8915C98` |
| 同结构参考 GS | `1DE14F90662DADF5823C37F3BFA9560A4C643E0F2143A3F0B914DFF2540BC292` |

## 实际处理

本轮没有写入目标 EXE/GS 二进制。

原因：只读复核发现当前目标已经满足第 0 步 active 链路边界：

- EXE 保留 ISRO 风格 UI：`0x21 -> 0x12E39EF`。
- active message-map base/entries 已是原 CSRO 链路：`0x00EC21B4 / 0x00FFE1E8`。
- GS client-message filter slot 已等于 `D:\Files\SR_GameServer.exe` 同结构参考：`0x004C8410`。
- `_REFSKILV` 是用户补丁，必须保留。

本轮只修改本地工具脚本：

- `tools\check_reverse_return_phase10_ui_only_restore.py`
  - 将旧检查 `gs_refskill_string_not_polluted` 改为 `gs_refskilv_user_patch_preserved`。
- `tools\apply_isro_reverse_return_phase10_ui_only_restore.py`
  - 移除会把 `_REFSKILV` 清成 `_REFSKILL` 的逻辑，避免后续误执行。

## 静态验证

`python .\tools\check_reverse_return_phase10_ui_only_restore.py --json`

结果：`7 pass / 0 fail`

关键通过项：

- `ui_bridge_is_preserved`
- `right_click_type_0x21_still_opens_isro_style_ui`
- `message_map_base_restored_to_original_csro`
- `message_map_entries_restored_to_original_csro`
- `gs_client_msg_filter_restored_to_same_structure_reference`
- `gs_refskilv_user_patch_preserved`

`python .\tools\check_reverse_return_phase11_party_enable_gate.py --json`

结果：`15 pass / 0 fail / 1 info`

## 结论

第 0 步静态闭环：保留 ISRO UI，同时确认 GS active 返回链路已经恢复/保持在 `D:\Files\SR_GameServer.exe` 参考状态。下一步才能进入“单人时移动到队友位置必须置灰”的真实链路定位。

## 禁止复用的旧口径

- 禁止再用旧 `gs_refskill_string_not_polluted` 把 `_REFSKILV` 判红。
- 禁止为了让 Phase10 旧检查通过而清理 `_REFSKILV`。
- 禁止把第 0 步理解为恢复旧 CSRO 三按钮 UI。
