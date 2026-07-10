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
