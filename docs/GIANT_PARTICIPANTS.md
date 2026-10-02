# Giant participant census

The Giant keeps its 0.25% direct type probability, 20-minute lifetime and +4 reward.
Its target is now `max(1, min(15, verified human accounts that are not deleted))`.
The target is fixed before sending the appearance, including a Giant hidden by a
Mystery. Other Hisopos do not invoke the census.

## Configuration

Register an application at <https://my.telegram.org> under API development tools.
Add `TELEGRAM_API_ID` (positive integer) and `TELEGRAM_API_HASH` (32 hexadecimal
characters) to the private `.env` or production bot environment. Never commit
these values or paste them into logs. The existing bot token authenticates the
same bot identity; no user account, phone-code login or userbot session is used.
The application ID belongs to the registered application, not the bot identity.

The existing secret-installation, patch and boolean-status scripts support both
keys. The Windows panel preserves advanced `.env` keys when saving its fields.
Configuring production or deploying requires a separately authorized operation.

## Requests and completion

Telethon uses an in-memory session, created lazily at the first Giant and reused
until shutdown. No session files are written. MTProto updates are disabled:
the existing Bot API polling remains the sole application update consumer.
The authenticated MTProto user ID must match the Bot API bot ID and be a bot.
For a cold supergroup, Telethon resolves its peer with a `getChannels` request
using Telegram's documented zero hash for bots. It caches and uses the returned
full access hash for participant requests; a zero hash alone was rejected by
`getParticipants` in the live private-group check.

Basic groups return participants and user records in one full-chat request.
Supergroups return pages of up to 200 members, with `bot`/`deleted` flags in the
same response. Only actual member IDs count, and duplicates are ignored.
No per-user request is made. Scanning and requesting further pages stop as soon
as 15 eligible identities have been verified. For fewer than 15, every identity
must be known, pagination must be complete and stable, and the returned member
count must match the full group total. This last check adds a full-channel request
for supergroups. An empty complete group still produces a target of 1.

Missing credentials, denied access, incomplete/changing lists and census timeouts
prevent that Giant appearance before a photo or spawn record is created. The
existing error handler reports the exact safe reason to the configured log chat;
scheduled appearances also retain their existing failed-job state. No guessed
target or fallback to the old total-minus-one calculation is used. Other games
continue running. A complete census cannot establish who is currently online.

Bot authentication permits one request retry for a data-center migration and two
connection retries, with the final safe RPC error retained. The whole operation,
including waiting for the shared connection lock, has a
30-second deadline. Flood waits are reported rather than sleeping indefinitely.
Shutdown disconnects the owned MTProto connection, including when another service
needs cleanup. Unit tests use real Telegram constructors and mocked RPC responses;
they do not send Telegram messages or authenticate a real account.

## Verification

Run `python -m pytest`, `python -m coverage run -m pytest`,
`python -m coverage json`, `python scripts/check_coverage.py` and
`python scripts/runtime_versions.py` from the project virtual environment.
Dependency changes also require the Docker test and runtime targets documented
in the repository workflows. A real read-only smoke check requires private API
credentials and bot membership/access to the designated test group.

References: [bot authentication](https://core.telegram.org/method/auth.importBotAuthorization),
[participant pages](https://core.telegram.org/method/channels.getParticipants),
[user flags](https://core.telegram.org/constructor/user),
[bot access hashes](https://core.telegram.org/api/peers#access-hash).
