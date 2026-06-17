# Phase11 修复前计划：保留 _REFSKILV 与队员置灰

记录日期：2026-06-17

## 本轮目标
1. 保留当前 ISRO 风格返回 UI。
2. 保留旧 CSRO 返回功能链路。
3. 保留用户补丁 `_REFSKILV`。
4. 只定位并修复 `移动至队员位置` 在单人状态下没有置灰的问题。

## 当前冻结事实
- freeze evidence: `C:\Users\43584\Documents\添加ISRO的返回功能\evidence\freeze-isro-return-phase11-baseline-20260617-010116.json`
- live EXE: `F:\CSRO客户端\SRO_Client.exe` SHA256 `2311872E2C7825684EF5EA6D10BCBBE8792DEE98AD6FCF92005B26CCDCA33E3F`
- live GS: `D:\CSRO\8-SR_GameServer.exe` SHA256 `B5C56F6A92B317C1701E1CF9E963754E4A0A52FFA74ACEFD91BC1E1DF8915C98`
- reference GS: `D:\Files\SR_GameServer.exe` SHA256 `1DE14F90662DADF5823C37F3BFA9560A4C643E0F2143A3F0B914DFF2540BC292`
- Phase11 checker: `C:\Users\43584\Documents\添加ISRO的返回功能\tools\check_reverse_return_phase11_baseline.py`，当前静态结果 `12 pass / 0 fail`
- 本记录未执行游戏内验证，未声明返回功能或队员置灰已经修复。

## 禁止路线
- 禁止清理 `_REFSKILV`。
- 禁止整表替换 message-map。
- 禁止把旧按钮 `0xC8/0xC9/0xCA/0xCB` 接到新 handler。
- 禁止只看静态字符串或 `0x12E39EF` 就宣布成功。
- 禁止未备份就写 EXE/GS。

## 本轮停止条件
- 如果只读对比不能证明唯一的队员置灰候选链路，本轮立即停止，只输出候选报告，不写 EXE/GS 二进制。

## 验收
- Phase11 baseline checker 必须通过。
- 第一次、第二次右键返回卷轴不闪退。
- 旧 CSRO 返回功能可用。
- 单人状态下 `移动至队员位置` 灰色不可选。
- 2 人及以上组队时 `移动至队员位置` 才可选。
- 同时间段无新 dump / FatalLog。
