from __future__ import annotations

from ..commands import Command
from .backup import COMMANDS as BACKUP_COMMANDS
from .blacklist import COMMANDS as BLACKLIST_COMMANDS
from .chats import COMMANDS as CHATS_COMMANDS
from .config import COMMANDS as CONFIG_COMMANDS
from .debug import COMMANDS as DEBUG_COMMANDS
from .galerazas import COMMANDS as GALERAZAS_COMMANDS
from .help import COMMANDS as HELP_COMMANDS
from .hola import COMMANDS as HOLA_COMMANDS
from .nivel import COMMANDS as NIVEL_COMMANDS
from .novedad import COMMANDS as NOVEDAD_COMMANDS
from .reportar import COMMANDS as REPORTAR_COMMANDS
from .salir import COMMANDS as SALIR_COMMANDS
from .triggers import COMMANDS as TRIGGERS_COMMANDS


COMMANDS: dict[str, Command] = {
    **HELP_COMMANDS,
    **HOLA_COMMANDS,
    **NIVEL_COMMANDS,
    **BLACKLIST_COMMANDS,
    **NOVEDAD_COMMANDS,
    **REPORTAR_COMMANDS,
    **BACKUP_COMMANDS,
    **DEBUG_COMMANDS,
    **CHATS_COMMANDS,
    **CONFIG_COMMANDS,
    **GALERAZAS_COMMANDS,
    **TRIGGERS_COMMANDS,
    **SALIR_COMMANDS,
}
