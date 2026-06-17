# Task 1：live 状态冻结与备份记录

轮次：`phase-isro-new-return-actions-20260617`

## 结论

已重新冻结本轮 live 状态，并创建 EXE/GS 双文件备份。当前未写入任何二进制补丁。

## live 文件

| 文件 | SHA256 | 大小 | LastWriteTime |
| --- | --- | ---: | --- |
| `F:\CSRO客户端\SRO_Client.exe` | `280C277CF73E93DBA9F384722653BD630CCA0EA8531EBCA387D792FAB41DB70E` | 13045760 | `2026-06-17 09:51:36` |
| `D:\CSRO\8-SR_GameServer.exe` | `B5C56F6A92B317C1701E1CF9E963754E4A0A52FFA74ACEFD91BC1E1DF8915C98` | 9949184 | `2026-06-17 10:07:55` |

## 参考文件

| 文件 | SHA256 | 大小 | LastWriteTime |
| --- | --- | ---: | --- |
| `F:\ISRO客户端国服\sro_client.exe` | `5AAE7E89985FEAFC4BB4273CAF73FB338213771C3488C756013B65182170ECB0` | 14196736 | `2026-06-11 19:15:50` |
| `F:\SR_GameServer.exe` | `6491737E65454C577CE72384C30DBEC72E57F9B8ECD064D8B4D1ABB42D8EC302` | 12218368 | `2025-02-02 05:47:54` |

## 进程锁检查

命令：

```powershell
Get-Process | Where-Object { $_.Path -in @('F:\CSRO客户端\SRO_Client.exe','D:\CSRO\8-SR_GameServer.exe') } | Select-Object Id,ProcessName,Path
```

结果：未返回锁定进程。

## 备份

备份目录：

`C:\Users\43584\Documents\添加ISRO的返回功能\backups\phase-isro-new-return-actions-20260617`

备份文件：

- `SRO_Client.exe`
- `8-SR_GameServer.exe`

manifest：

`evidence\2026-06-17-phase-isro-new-return-actions-manifest.json`

## 状态

- 已完成：live hash、大小、时间记录。
- 已完成：写入前进程锁检查。
- 已完成：本轮 EXE/GS 双文件备份。
- 未执行：客户端补丁写入。
- 未执行：GS 补丁写入。

## 已完成 / 阻塞 / 待补证据

- 已完成：本轮 live 冻结、备份与 manifest 记录。
- 阻塞：无。
- 待补证据：任务 2-4 的运行时入口、门禁和发包证据。
