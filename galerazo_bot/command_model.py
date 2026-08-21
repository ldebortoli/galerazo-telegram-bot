from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

from .roles import CommandContext, UserLevel

if TYPE_CHECKING:
    from .database import Database


CommandResult = Union[Optional[str], Awaitable[Optional[str]]]
CommandHandler = Callable[[CommandContext, "Database"], CommandResult]


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: CommandHandler
    min_level: UserLevel = UserLevel.COMMON
    permission_error: str | None = None
    permission_error_key: str | None = None
    hidden: bool = False
    configurable_group: str | None = None
    command_key: str | None = None
    list_response: bool = False
    response_parse_mode: str | None = None

    def __post_init__(self) -> None:
        if self.command_key is None:
            object.__setattr__(self, "command_key", self.name.split(maxsplit=1)[0])
