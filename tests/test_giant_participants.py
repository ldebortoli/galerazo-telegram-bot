from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from telethon import functions, types
from telethon.errors import RPCError

from galerazo_bot import config
from galerazo_bot import giant_participants as census


BOT_ID = 42
CHANNEL_ID = 123
CHAT_ID = "-1000000000123"
DATE = datetime(2026, 10, 2, tzinfo=timezone.utc)


def settings(**overrides):
    base = config.Settings(
        telegram_bot_token="test-token", telegram_dev_user_ids=frozenset(),
        telegram_log_chat_id=None, telegram_announcements_chat_id=None,
        database_path=Path("unused.sqlite3"), telegram_api_id=12345,
        telegram_api_hash="a" * 32,
    )
    return replace(base, **overrides)


def users(ids, **flags):
    return [types.User(user_id, **flags) for user_id in ids]


def page(accounts, *, count=None, participants=None):
    members = [types.ChannelParticipant(user.id, DATE) for user in accounts]
    return types.channels.ChannelParticipants(
        count=len(accounts) if count is None else count,
        participants=members if participants is None else participants,
        chats=[], users=accounts,
    )


def full_channel(count, *, visible=True):
    full = types.ChannelFull(
        CHANNEL_ID, "", 0, 0, 0, types.PhotoEmpty(0),
        types.PeerNotifySettings(), [], 0,
        participants_count=count, can_view_participants=visible,
    )
    return types.messages.ChatFull(full, [], [])


def basic(accounts, *, count=None, participants=None):
    members = [types.ChatParticipant(user.id, 1, DATE) for user in accounts]
    group = types.Chat(
        CHANNEL_ID, "test", types.ChatPhotoEmpty(),
        len(accounts) if count is None else count, DATE, 1,
    )
    full = types.ChatFull(
        CHANNEL_ID, "", types.ChatParticipants(
            CHANNEL_ID, members if participants is None else participants, 1,
        ), types.PeerNotifySettings(),
    )
    return types.messages.ChatFull(full, [group], accounts)


@pytest.fixture
def client():
    result = AsyncMock()
    result.sign_in.return_value = types.User(BOT_ID, bot=True)
    result.get_input_entity.return_value = types.InputPeerChannel(CHANNEL_ID, 88)
    return result


@pytest.fixture
def factory(client):
    with patch.object(census, "TelegramClient", return_value=client) as constructor:
        yield constructor


@pytest.mark.asyncio
async def test_small_census_excludes_bots_deleted_and_nonmembers(client, factory):
    accounts = users(range(1, 6)) + users([BOT_ID, 60], bot=True) + users([61], deleted=True)
    response = page(accounts)
    response.users += users([99])  # Related users returned by Telegram are not members.
    client.side_effect = [response, full_channel(8), response, full_channel(8)]
    counter = census.GiantParticipantCounter(settings(), str(BOT_ID))
    assert await counter.count(CHAT_ID) == 5
    assert await counter.count(CHAT_ID) == 5
    factory.assert_called_once()
    args, options = factory.call_args
    assert args == (None, 12345, "a" * 32)  # In-memory session.
    assert options["receive_updates"] is False
    assert options["flood_sleep_threshold"] == 0
    assert options["request_retries"] == 1  # Bot login may migrate to another DC.
    assert options["raise_last_call_error"] is True
    client.sign_in.assert_awaited_once_with(bot_token="test-token")
    request = client.await_args_list[0].args[0]
    assert isinstance(request, functions.channels.GetParticipantsRequest)
    assert request.channel.channel_id == CHANNEL_ID
    assert request.channel.access_hash == 88
    client.get_input_entity.assert_awaited_with(types.PeerChannel(CHANNEL_ID))
    assert (request.offset, request.limit, request.hash) == (0, 200, 0)
    await counter.close()
    await counter.close()
    client.disconnect.assert_awaited_once()
    assert counter._client is None


@pytest.mark.asyncio
@pytest.mark.parametrize("account_list", [[], users([42, 44], bot=True), users([4, 5], deleted=True)])
async def test_complete_zero_census_requires_one(account_list, client, factory):
    client.side_effect = [page(account_list), full_channel(len(account_list))]
    assert await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID) == 1


@pytest.mark.asyncio
async def test_stops_at_fifteen_even_with_unknown_later_members(client, factory):
    response = page(users(range(1, 16)), count=999)
    response.participants.append(types.ChannelParticipant(900, DATE))
    client.return_value = response
    assert await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID) == 15
    client.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("human_count", [14, 15])
async def test_pages_through_deleted_accounts_and_stops_without_extra_rpc(human_count, client, factory):
    deleted = users(range(1000, 1200), deleted=True)
    humans = users(range(1, human_count + 1))
    replies = [page(deleted, count=200 + human_count), page(humans, count=200 + human_count)]
    if human_count < 15:
        replies.append(full_channel(200 + human_count))
    client.side_effect = replies
    assert await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID) == human_count
    assert client.await_count == len(replies)
    assert client.await_args_list[1].args[0].offset == 200


@pytest.mark.asyncio
async def test_duplicate_identities_do_not_inflate_target(client, factory):
    accounts = users([1, 2, 2, BOT_ID], bot=False)
    client.side_effect = [page(accounts, count=3), full_channel(3)]
    assert await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID) == 2


@pytest.mark.asyncio
async def test_repeated_full_page_fails_instead_of_looping(client, factory):
    first = page(users(range(1000, 1200), deleted=True), count=500)
    client.side_effect = [first, first]
    with pytest.raises(census.GiantParticipantCountError, match="no avanzo"):
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)
    assert client.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [types.channels.ChannelParticipantsNotModified(), page([], count=-1)])
async def test_unverifiable_telegram_response_is_rejected(response, client, factory):
    client.return_value = response
    with pytest.raises(census.GiantParticipantCountError, match="verificable"):
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [
    page(users([1]), count=2),
    page([], count=1, participants=[types.ChannelParticipant(1, DATE)]),
    page([types.UserEmpty(1)]),
])
async def test_incomplete_census_never_returns_partial_target(response, client, factory):
    client.return_value = response
    with pytest.raises(census.GiantParticipantCountError, match="incompleto"):
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)
    client.assert_awaited_once()


@pytest.mark.asyncio
async def test_membership_change_between_pages_is_rejected(client, factory):
    client.side_effect = [
        page(users(range(1000, 1200), deleted=True), count=201),
        page(users([1]), count=202),
    ]
    with pytest.raises(census.GiantParticipantCountError, match="cambio"):
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("metadata", [full_channel(1, visible=False), full_channel(999), basic([])])
async def test_recent_filter_subset_or_hidden_members_is_rejected(metadata, client, factory):
    client.side_effect = [page(users([1])), metadata]
    with pytest.raises(census.GiantParticipantCountError, match="completo del supergrupo"):
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("human_count", [0, 3, 15])
async def test_basic_group_is_counted_in_one_request(human_count, client, factory):
    client.return_value = basic(users(range(1, human_count + 1)) + users([BOT_ID], bot=True))
    assert await census.GiantParticipantCounter(settings(), "42").count("-123") == max(1, human_count)
    client.assert_awaited_once()
    assert isinstance(client.await_args.args[0], functions.messages.GetFullChatRequest)
    assert client.await_args.args[0].chat_id == CHANNEL_ID


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["forbidden", "unknown", "missing-chat", "wrong-count"])
async def test_basic_group_requires_complete_accessible_members(scenario, client, factory):
    response = basic(users([1]))
    if scenario == "forbidden":
        response.full_chat.participants = types.ChatParticipantsForbidden(CHANNEL_ID)
    elif scenario == "unknown":
        response.users = []
    elif scenario == "missing-chat":
        response.chats = []
    else:
        response.chats[0].participants_count = 99
    client.return_value = response
    with pytest.raises(census.GiantParticipantCountError):
        await census.GiantParticipantCounter(settings(), "42").count("-123")


@pytest.mark.asyncio
async def test_restricted_member_with_user_peer_still_counts(client, factory):
    member = SimpleNamespace(peer=types.PeerUser(1), left=False)
    client.side_effect = [page(users([1]), participants=[member]), full_channel(1)]
    assert await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("member", [SimpleNamespace(peer=types.PeerChannel(1)), SimpleNamespace(peer=types.PeerUser(1), left=True)])
async def test_nonmember_or_unknown_peer_is_rejected(member, client, factory):
    client.return_value = page(users([1]), participants=[member])
    with pytest.raises(census.GiantParticipantCountError, match="miembros desconocidos"):
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("credentials", [
    {"telegram_api_id": None}, {"telegram_api_hash": None},
    {"telegram_api_id": 0}, {"telegram_api_id": -1},
    {"telegram_api_id": 2_147_483_648}, {"telegram_api_hash": "private-invalid-hash"},
])
async def test_invalid_credentials_never_connect_or_leak(credentials, factory):
    with pytest.raises(census.GiantParticipantCountError) as caught:
        await census.GiantParticipantCounter(settings(**credentials), "42").count(CHAT_ID)
    assert "private-invalid-hash" not in str(caught.value)
    factory.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("identity", [None, types.User(42), types.User(43, bot=True)])
async def test_only_expected_bot_identity_can_authenticate(identity, client, factory):
    client.sign_in.return_value = identity
    counter = census.GiantParticipantCounter(settings(), "42")
    with pytest.raises(census.GiantParticipantCountError, match="identidad"):
        await counter.count(CHAT_ID)
    client.disconnect.assert_awaited_once()
    client.assert_not_awaited()
    assert counter._client is None


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [OSError("secret-token"), ValueError("secret-token"), RPCError(None, "secret-token", 400), TimeoutError("secret-token")])
async def test_rpc_errors_are_sanitized(exception, client, factory):
    client.side_effect = exception
    with pytest.raises(census.GiantParticipantCountError) as caught:
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)
    assert "secret-token" not in str(caught.value)
    assert type(exception).__name__ in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.asyncio
async def test_failed_auth_is_disconnected_and_disconnect_failure_is_sanitized(client, factory, caplog):
    client.sign_in.side_effect = OSError("secret-token")
    client.disconnect.side_effect = OSError("secret-token")
    counter = census.GiantParticipantCounter(settings(), "42")
    with pytest.raises(census.GiantParticipantCountError):
        await counter.count(CHAT_ID)
    assert "secret-token" not in caplog.text
    assert "conexion MTProto fallida" in caplog.text
    assert counter._client is None


@pytest.mark.asyncio
async def test_connection_failure_is_disconnected(client, factory):
    client.connect.side_effect = OSError("network unavailable")
    with pytest.raises(census.GiantParticipantCountError, match="OSError"):
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)
    client.disconnect.assert_awaited_once()
    client.sign_in.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancellation_propagates_and_cleans_up_auth(client, factory):
    client.sign_in.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_total_deadline_covers_authentication(client, factory):
    async def delayed_auth(**_):
        await asyncio.Event().wait()
    client.sign_in.side_effect = delayed_auth
    with patch.object(census, "CENSUS_TIMEOUT_SECONDS", 0.01):
        with pytest.raises(census.GiantParticipantCountError, match="TimeoutError"):
            await census.GiantParticipantCounter(settings(), "42").count(CHAT_ID)
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("chat_id", ["123", "not-a-chat-id"])
async def test_only_groups_are_valid_destinations(chat_id, client, factory):
    with pytest.raises(census.GiantParticipantCountError):
        await census.GiantParticipantCounter(settings(), "42").count(chat_id)
    client.assert_not_awaited()


@pytest.mark.asyncio
async def test_concurrent_counts_reuse_one_authenticated_client(client, factory):
    client.return_value = page(users(range(1, 16)))
    counter = census.GiantParticipantCounter(settings(), "42")
    assert await asyncio.gather(counter.count(CHAT_ID), counter.count(CHAT_ID)) == [15, 15]
    factory.assert_called_once()
    client.sign_in.assert_awaited_once()
    assert client.await_count == 2


@pytest.mark.parametrize("raw, expected", [("", None), ("  ", None), ("12345", 12345)])
def test_optional_api_id(raw, expected):
    assert config._optional_api_id(raw) == expected


@pytest.mark.parametrize("raw", ["0", "-1", "2147483648", "secret-invalid-value"])
def test_invalid_api_id_error_is_sanitized(raw):
    with pytest.raises(ValueError) as caught:
        config._optional_api_id(raw)
    assert raw not in str(caught.value)


def test_load_api_credentials_and_hide_hash_from_repr():
    with patch.object(config, "load_dotenv"), patch.dict("os.environ", {
        "TELEGRAM_API_ID": "12345", "TELEGRAM_API_HASH": "b" * 32,
    }, clear=True):
        loaded = config.load_settings()
    assert loaded.telegram_api_id == 12345
    assert loaded.telegram_api_hash == "b" * 32
    assert "b" * 32 not in repr(loaded)
