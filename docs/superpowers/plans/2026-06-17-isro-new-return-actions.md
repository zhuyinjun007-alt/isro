# ISRO 新增返回功能实施计划

> **给智能体执行者：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务执行本计划。步骤使用 `- [ ]` 复选框语法跟踪。

**目标：** 在保留 CSRO 原有返回链路的前提下，闭合 `移动至队员位置` 和 `移动至使用者指定的位置` 两个 ISRO 新增返回功能。

**架构：** 分三层推进：先确认客户端返回 UI、旧按钮链路和置灰状态稳定，再只给 `0xCC/0xCF` 增加客户端事件与发包链路，最后对齐 GS 校验与传送行为。每一层必须先验证通过，才允许进入下一层写入。

**技术栈：** PowerShell、Git、GitHub API、仓库内 `tools/` 逆向与补丁脚本、EXE/GS 二进制、客户端 Dump、GS FatalLog、游戏内复现记录。

---

### 任务 1：重新冻结 live 状态并收集证据

**文件：**
- 新建：`reports\2026-06-17-phase-isro-new-return-actions-task1-freeze.md`
- 新建：`evidence\2026-06-17-phase-isro-new-return-actions-manifest.json`

- [ ] **步骤 1：记录 live EXE/GS 的 hash、大小和时间**

运行：
```powershell
Get-FileHash 'F:\CSRO客户端\SRO_Client.exe' -Algorithm SHA256
Get-Item 'F:\CSRO客户端\SRO_Client.exe' | Select-Object Length,LastWriteTime
Get-FileHash 'D:\CSRO\8-SR_GameServer.exe' -Algorithm SHA256
Get-Item 'D:\CSRO\8-SR_GameServer.exe' | Select-Object Length,LastWriteTime
```

预期：把最新 hash、大小、时间写入 `evidence\2026-06-17-phase-isro-new-return-actions-manifest.json`。

- [ ] **步骤 2：写入前确认 EXE/GS 没有被运行进程锁定**

运行：
```powershell
Get-Process | Where-Object { $_.Path -in @('F:\CSRO客户端\SRO_Client.exe','D:\CSRO\8-SR_GameServer.exe') } | Select-Object Id,ProcessName,Path
```

预期：没有锁定进程；如果存在锁定进程，停止本任务并在报告中记录阻塞。

- [ ] **步骤 3：创建本轮双文件备份**

运行：
```powershell
New-Item -ItemType Directory -Force -Path "C:\Users\43584\Documents\添加ISRO的返回功能\backups\phase-isro-new-return-actions-20260617" | Out-Null
Copy-Item 'F:\CSRO客户端\SRO_Client.exe' "C:\Users\43584\Documents\添加ISRO的返回功能\backups\phase-isro-new-return-actions-20260617\SRO_Client.exe"
Copy-Item 'D:\CSRO\8-SR_GameServer.exe' "C:\Users\43584\Documents\添加ISRO的返回功能\backups\phase-isro-new-return-actions-20260617\8-SR_GameServer.exe"
```

预期：备份目录里同时存在 `SRO_Client.exe` 和 `8-SR_GameServer.exe`。

---

### 任务 2：重新确认客户端入口与旧按钮链路

**文件：**
- 新建：`reports\2026-06-17-phase-isro-new-return-actions-task2-client-entry.md`
- 新建或修改：`tools\check_reverse_return_phase10_ui_only_restore.py`
- 新建或修改：`tools\check_reverse_return_phase11_party_enable_gate.py`
- 新建：`tools\find_reverse_return_entry.py`
- 新建：`tools\trace_reverse_return_message_map.py`

- [ ] **步骤 1：运行现有静态检查**

运行：
```powershell
python .\tools\check_reverse_return_phase10_ui_only_restore.py --json
python .\tools\check_reverse_return_phase11_party_enable_gate.py --json
```

预期：检查结果只反映当前已知状态；如有新失败，先记录并停止写入。

- [ ] **步骤 2：确认真实右键入口仍是 `0x21`**

运行：
```powershell
python .\tools\find_reverse_return_entry.py
```

预期：输出确认 `0x21` 仍是真实右键返回卷轴入口，`0x2A/0x2B` 不作为 live 入口依据。

- [ ] **步骤 3：确认旧按钮仍归属 CSRO 原链路**

运行：
```powershell
python .\tools\trace_reverse_return_message_map.py
```

预期：`0xC8/0xC9/0xCA/0xCB` 仍走原 CSRO 链路，没有进入 `0xCC/0xCF` 新链路。

---

### 任务 3：定位并修复 `0xCC` 队员按钮置灰来源

**文件：**
- 新建：`reports\2026-06-17-phase-isro-new-return-actions-task3-client-gate.md`
- 新建：`tools\trace_team_member_enable_source.py`
- 新建：`tools\apply_client_party_enable_patch.py`
- 新建：`tools\check_reverse_return_party_gate.py`

- [ ] **步骤 1：只读定位队员按钮 enable 的运行时状态来源**

运行：
```powershell
python .\tools\trace_team_member_enable_source.py
```

预期：输出 `0xCC` enable 判断读取的真实运行时来源、VA/raw offset 和证据链。

- [ ] **步骤 2：只补 `0xCC` 的 enable/read 路径**

运行：
```powershell
python .\tools\apply_client_party_enable_patch.py --round phase-isro-new-return-actions-20260617
```

预期：只改目标客户端字节；旧按钮链路不变。

- [ ] **步骤 3：验证 `0xCC` gate 静态证据**

运行：
```powershell
python .\tools\check_reverse_return_party_gate.py --json
```

预期：单人状态 `0xCC` 不可选，组队状态可选；旧按钮无回归。

---

### 任务 4：闭合 `0xCC/0xCF` 客户端事件与发包链路

**文件：**
- 新建：`reports\2026-06-17-phase-isro-new-return-actions-task4-client-events.md`
- 新建：`tools\trace_reverse_return_new_handlers.py`
- 新建：`tools\apply_client_new_return_handlers.py`
- 新建：`tools\trace_reverse_return_packets.py`

- [ ] **步骤 1：写入前追踪现有 `0xCC/0xCF` stub 路径**

运行：
```powershell
python .\tools\trace_reverse_return_new_handlers.py
```

预期：输出当前 handler slot、调用方和缺口，不写二进制。

- [ ] **步骤 2：只让 `0xCC/0xCF` 接入新增 handler**

运行：
```powershell
python .\tools\apply_client_new_return_handlers.py --round phase-isro-new-return-actions-20260617
```

预期：旧按钮仍走旧链路，只有 `0xCC/0xCF` 进入新增 handler。

- [ ] **步骤 3：运行时确认新按钮发包**

运行：
```powershell
python .\tools\trace_reverse_return_packets.py
```

预期：两个新增 handler 发出预期请求；第一次和第二次打开不崩溃。

---

### 任务 5：对齐 GS 校验与传送行为

**文件：**
- 新建：`reports\2026-06-17-phase-isro-new-return-actions-task5-gs.md`
- 新建：`tools\trace_isro_gs_return_paths.py`
- 新建：`tools\apply_gs_return_action_patch.py`
- 新建：`tools\check_reverse_return_gs_alignment.py`

- [ ] **步骤 1：确认 ISRO GS 参考行为**

运行：
```powershell
python .\tools\trace_isro_gs_return_paths.py
```

预期：输出两个新增返回动作在 ISRO GS 中的收包、校验、传送和失败拒绝证据。

- [ ] **步骤 2：只补 CSRO GS 缺失分支**

运行：
```powershell
python .\tools\apply_gs_return_action_patch.py --round phase-isro-new-return-actions-20260617
```

预期：GS 只增加缺失校验/传送边；保留 `_REFSKILV` 和无关补丁。

- [ ] **步骤 3：运行 GS 静态对齐检查**

运行：
```powershell
python .\tools\check_reverse_return_gs_alignment.py --json
```

预期：新增 GS 分支可解析，旧行为仍保持。

---

### 任务 6：端到端验收、回滚与 issue 回复

**文件：**
- 新建：`reports\2026-06-17-phase-isro-new-return-actions-task6-smoke.md`
- 新建：`tools\record_reverse_return_smoke.py`
- 新建：`tools\restore_reverse_return_round.py`
- 新建：`tools\post_reverse_return_issue_comment.py`

- [ ] **步骤 1：运行游戏内冒烟验收**

运行：
```powershell
python .\tools\record_reverse_return_smoke.py
```

预期：记录第一次右键、第二次右键、旧按钮、队员按钮置灰、组队启用和两个新增功能结果。

- [ ] **步骤 2：如有失败，立即恢复本轮备份**

运行：
```powershell
python .\tools\restore_reverse_return_round.py --round phase-isro-new-return-actions-20260617
```

预期：EXE/GS hash 回到本轮备份值，失败 dump/FatalLog 保留。

- [ ] **步骤 3：用 UTF-8 方式回复 GitHub issue #2**

运行：
```powershell
python .\tools\post_reverse_return_issue_comment.py --issue 2 --round phase-isro-new-return-actions-20260617
```

预期：issue 评论包含可点击的文档、报告和提交链接；中文不乱码。

---

## 计划自审记录

- 规格覆盖：覆盖 live 冻结、客户端稳定性、客户端事件、GS 校验、游戏内验收、失败回滚和 issue 回复。
- 占位扫描：计划正文不包含待填轮次名或尖括号占位符。
- 命名一致：全篇使用同一轮次名 `phase-isro-new-return-actions-20260617`。
- 范围控制：只处理两个新增返回功能，不扩展到无关补丁或整文件覆盖。
