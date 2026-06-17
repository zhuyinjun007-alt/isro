# ISRO Return Acceptance Design

## Goal

Complete the CSRO return-scroll repair so in-game acceptance can pass:

- Right-clicking the return scroll the first and second time must not crash the client.
- The return UI must keep the ISRO-style five action rows plus cancel.
- Existing CSRO actions `0xC8`, `0xC9`, `0xCA`, and `0xCB` must keep the original CSRO chain.
- New ISRO actions `0xCC` and `0xCF` must be connected through the client and game server.
- `Move to party member position` must be disabled when solo and enabled only when the player is in a party of at least two.
- No new same-window client dump or server FatalLog may appear during acceptance.

## Scope

In scope:

- `F:\CSRO客户端\SRO_Client.exe`
- `D:\CSRO\8-SR_GameServer.exe`
- Read-only comparison against `F:\ISRO客户端国服\sro_client.exe` and `F:\SR_GameServer.exe`
- Static diagnostic and patch scripts under this record repository or the existing evidence/tooling directory
- Reports, manifests, backups, and GitHub issue progress comments

Out of scope:

- Database edits
- PK2 or Media resource edits
- DLL, launcher, ShardManager, and unrelated game patches
- Whole-file rollback to original reference binaries
- Any route that reuses previously failed full message-map replacement or old-button handler pollution

## Evidence Already Known

The current records establish these constraints:

- The real return-scroll entry is `0x21`.
- Existing CSRO return buttons must not enter the new handler table.
- Full message-map replacement and broad lifecycle guessing caused old functions to fail or the client to crash.
- UI display success is not functional success.
- Static checks are only admission checks; final success requires in-game acceptance.
- Each repair round must back up both EXE and GS before any write and restore that round's backup on failure.

## Architecture

Use a conservative two-layer repair:

1. Preserve the current ISRO-style UI entry and old CSRO runtime slots.
2. Add only missing, narrowly scoped behavior for the new `0xCC` and `0xCF` actions after evidence proves the specific gap.

The client layer owns UI state, button enablement, action dispatch, packet emission, and lifecycle safety. The game server layer owns packet receive, validation, party/save-position checks, and teleport execution. The two layers are validated together only after both have evidence and backups.

## Data Flow

Client flow:

1. Right-click return scroll enters `SetMsgBoxHandler` through `arg0=0x21`.
2. Existing UI bridge opens the ISRO-style return dialog.
3. Old buttons `0xC8` to `0xCB` remain mapped to original CSRO handlers.
4. New button `0xCC` is enabled only when the real runtime party member condition is true.
5. New buttons `0xCC` and `0xCF` emit their intended request packets without corrupting old handlers or dialog lifecycle.

Server flow:

1. GS receives the request for party-member movement or user-appointed movement.
2. GS validates item, player state, party count or saved position state, and target eligibility.
3. GS performs teleport or rejects safely.
4. Failure must not crash client or server and must not pollute old return paths.

## Error Handling And Rollback

Before each write:

- Confirm target files are writable and not locked by running processes.
- Copy both live EXE and GS into a round-specific backup directory.
- Record SHA256, LastWriteTime, file size, target VA, raw offset, old bytes, new bytes, and reason.

After any failed static check or game acceptance:

- Restore both files from the current round backup.
- Recompute hashes.
- Preserve dump, FatalLog, screenshots, and report.
- Do not stack the next patch on top of a failed state.

## Testing Strategy

Use a red-green style static gate before binary writes:

- First create a diagnostic that reports the current failure or missing evidence.
- Confirm it fails or reports blocked evidence on the live files.
- Only then write the minimal patch for one hypothesis.
- Re-run the same diagnostic and existing regression checks.

Static checks must cover:

- `0x21` return entry still reaches the intended UI path.
- Old `0xC8` to `0xCB` handlers remain on old CSRO chain.
- New `0xCC` and `0xCF` are not implemented by replacing the whole message-map.
- Party-member enablement uses a verified runtime condition, not a previously failed guess.
- GS and EXE hashes and write times reflect the actual round's intended writes.

Manual acceptance remains required:

- First and second right-click return-scroll open without crash.
- Old return actions still work.
- Solo `Move to party member position` is disabled.
- Two-player party state enables and executes party-member movement.
- `Move to user-appointed position` does not crash and behaves as expected.
- No same-window dump or FatalLog appears.

## Delivery

Each execution round must produce:

- A backup directory.
- A patch manifest.
- Static check output.
- A short report under `reports/`.
- A GitHub issue comment when the stage meaningfully advances or blocks.

## Approval

User approved this conservative design on 2026-06-17 and requested continued Chinese progress updates in GitHub issues.
