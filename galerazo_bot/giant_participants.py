"""Read-only MTProto census for cooperative Giant Hisopos."""
from __future__ import annotations

import asyncio
import logging
import re

from telethon import TelegramClient, functions, types, utils
from telethon.errors import RPCError

from .config import Settings
from .hisopos import HISOPO_GIANT_MAX_HELPERS, giant_required_helpers


PAGE_SIZE = 200
CENSUS_TIMEOUT_SECONDS = 30
logger = logging.getLogger(__name__)


class GiantParticipantCountError(RuntimeError):
    """The census cannot prove a safe target; details never contain credentials."""


class GiantParticipantCounter:
    def __init__(self, settings: Settings, bot_user_id: str) -> None:
        self.settings = settings
        self.bot_user_id = int(bot_user_id)
        self._client: TelegramClient | None = None
        self._lock = asyncio.Lock()

    async def count(self, chat_id: str) -> int:
        if not self.settings.telegram_api_id or not self.settings.telegram_api_hash:
            raise GiantParticipantCountError("Faltan TELEGRAM_API_ID y TELEGRAM_API_HASH.")
        if not 0 < self.settings.telegram_api_id <= 2_147_483_647 or not re.fullmatch(
            r"[0-9a-fA-F]{32}", self.settings.telegram_api_hash
        ):
            raise GiantParticipantCountError("La configuracion MTProto no es valida.")
        try:
            async with asyncio.timeout(CENSUS_TIMEOUT_SECONDS):
                async with self._lock:
                    client = await self._connect()
                    real_id, peer_type = utils.resolve_id(int(chat_id))
                    if peer_type is types.PeerChannel:
                        humans = await self._channel_count(client, real_id)
                    elif peer_type is types.PeerChat:
                        humans = await self._basic_count(client, real_id)
                    else:
                        raise GiantParticipantCountError("El destino no es un grupo.")
                    return giant_required_helpers(humans)
        except (RPCError, OSError, ValueError, TimeoutError) as exc:
            raise GiantParticipantCountError(
                f"No se pudo completar el censo MTProto ({type(exc).__name__})."
            ) from None

    async def _connect(self) -> TelegramClient:
        if self._client is not None:
            return self._client
        transport_logger = logging.getLogger("galerazo_bot.mtproto_transport")
        transport_logger.setLevel(logging.WARNING)
        client = TelegramClient(
            None, self.settings.telegram_api_id, self.settings.telegram_api_hash,
            # One retry is needed for Telegram's bot-auth DC migration.
            receive_updates=False, request_retries=1, connection_retries=2,
            raise_last_call_error=True,
            flood_sleep_threshold=0, timeout=10, base_logger=transport_logger,
        )
        try:
            await client.connect()
            identity = await client.sign_in(bot_token=self.settings.telegram_bot_token)
            if (
                not isinstance(identity, types.User)
                or not identity.bot
                or identity.id != self.bot_user_id
            ):
                raise GiantParticipantCountError("La identidad MTProto no coincide con el bot.")
        except BaseException:
            try:
                await client.disconnect()
            except Exception:
                logger.warning("No se pudo cerrar una conexion MTProto fallida.")
            raise
        self._client = client
        return client

    async def close(self) -> None:
        async with self._lock:
            if self._client is not None:
                client, self._client = self._client, None
                await client.disconnect()

    def _scan(self, participants, users, seen: set[int], eligible: set[int]) -> bool:
        """Return whether identities are missing; only actual member IDs count."""
        by_id = {user.id: user for user in users}
        unknown = False
        for participant in participants:
            user_id = getattr(participant, "user_id", None)
            if user_id is None:
                peer = getattr(participant, "peer", None)
                if not isinstance(peer, types.PeerUser) or getattr(participant, "left", False):
                    raise GiantParticipantCountError("El listado contiene miembros desconocidos.")
                user_id = peer.user_id
            if user_id in seen:
                continue
            seen.add(user_id)
            user = by_id.get(user_id)
            if not isinstance(user, types.User):
                unknown = True
                continue
            if not user.bot and not user.deleted and user_id != self.bot_user_id:
                eligible.add(user_id)
                if len(eligible) == HISOPO_GIANT_MAX_HELPERS:
                    break
        return unknown

    async def _basic_count(self, client, chat_id: int) -> int:
        result = await client(functions.messages.GetFullChatRequest(chat_id))
        members = result.full_chat.participants
        if not isinstance(members, types.ChatParticipants):
            raise GiantParticipantCountError("Telegram no permite ver los miembros del grupo.")
        seen: set[int] = set()
        eligible: set[int] = set()
        unknown = self._scan(members.participants, result.users, seen, eligible)
        if len(eligible) == HISOPO_GIANT_MAX_HELPERS:
            return HISOPO_GIANT_MAX_HELPERS
        chat = next((item for item in result.chats if item.id == chat_id), None)
        if unknown or getattr(chat, "participants_count", None) != len(seen):
            raise GiantParticipantCountError("No se pudo confirmar el listado completo del grupo.")
        return len(eligible)

    async def _channel_count(self, client, chat_id: int) -> int:
        # Telethon resolves a cold bot peer via getChannels with a zero hash,
        # then caches the full hash required by participant requests.
        channel = utils.get_input_channel(
            await client.get_input_entity(types.PeerChannel(chat_id))
        )
        seen: set[int] = set()
        eligible: set[int] = set()
        unknown = False
        unstable = False
        expected: int | None = None
        offset = 0
        while True:
            page = await client(functions.channels.GetParticipantsRequest(
                channel, types.ChannelParticipantsRecent(), offset, PAGE_SIZE, 0,
            ))
            if not isinstance(page, types.channels.ChannelParticipants) or page.count < 0:
                raise GiantParticipantCountError("Telegram no devolvio un listado verificable.")
            if expected is None:
                expected = page.count
            elif expected != page.count:
                unstable = True
            before = len(seen)
            unknown = self._scan(page.participants, page.users, seen, eligible) or unknown
            if len(eligible) == HISOPO_GIANT_MAX_HELPERS:
                return HISOPO_GIANT_MAX_HELPERS
            offset += len(page.participants)
            if len(page.participants) < PAGE_SIZE or len(seen) >= page.count:
                break
            if len(seen) == before:
                raise GiantParticipantCountError("La paginacion de miembros no avanzo.")
        if unknown or unstable or len(seen) != expected:
            raise GiantParticipantCountError("El listado de miembros esta incompleto o cambio.")
        # The Recent filter may expose only a subset: verify the full member total
        # only when fewer than 15 humans were found. A proven 15 needs no extra RPC.
        full = await client(functions.channels.GetFullChannelRequest(channel))
        if (
            not isinstance(full.full_chat, types.ChannelFull)
            or not full.full_chat.can_view_participants
            or full.full_chat.participants_count != len(seen)
        ):
            raise GiantParticipantCountError("No se pudo confirmar el listado completo del supergrupo.")
        return len(eligible)
