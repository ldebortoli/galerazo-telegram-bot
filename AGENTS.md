<!-- codex-persistent-memory -->
# Persistent project memory

Before doing any work in this repository, read these files in order:

1. `.codex/CONTEXT.md`
2. `.codex/DECISIONS.md`
3. `.codex/BACKLOG.md`
4. `.codex/USER_QUEUE.md`
5. `.codex/SESSION_HANDOFF.md`

Then merge unprocessed `USER_QUEUE.md` items into `BACKLOG.md` without duplicates and reconcile `SESSION_HANDOFF.md` with the real repository state.

During work, update the corresponding `.codex/` files immediately when a task is completed, architecture changes, a decision is made, a problem is found or new work is discovered.

Before ending a session:

- update `BACKLOG.md` and `SESSION_HANDOFF.md`;
- append new technical decisions to `DECISIONS.md`;
- update `CONTEXT.md` only for stable project changes;
- validate the repository;
- commit and push when a remote is configured.

Do not expose or version `.env`, credentials, databases, logs, backups or local PID files.

<!-- codex-user-queue-execution -->
## Automatic user queue execution

`Procesadas` in `.codex/USER_QUEUE.md` means incorporated into `BACKLOG.md`, not completed. After handling the direct message that starts a run, automatically execute every unblocked queue-derived backlog task by priority. Continue until each is implemented, validated and moved to `DONE`, or record its precise blocker and continue with other executable queued work. Do not stop after triage or after only one queued task unless the user explicitly asks to pause, stop or only report status.

<!-- galerazo-bot-log-checkpoint -->
## Bot log checkpoint

Before ending every user instruction, run `python -m galerazo_bot.log_checkpoint`. It reads only new entries from `data/bot.log`. If it reports errors, investigate and fix them before finishing; after the entries are understood and addressed, run `python -m galerazo_bot.log_checkpoint --acknowledge` and then run the normal check once more. Never print `.env` or secrets while diagnosing logs.
