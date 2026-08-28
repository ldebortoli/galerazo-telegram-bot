from __future__ import annotations

from ..command_model import Command
from .apagar import COMMANDS as SHUTDOWN_COMMANDS
from .anuncio import COMMANDS as ANUNCIO_COMMANDS
from .backup import COMMANDS as BACKUP_COMMANDS
from .blacklist import COMMANDS as BLACKLIST_COMMANDS
from .chats import COMMANDS as CHATS_COMMANDS
from .config import COMMANDS as CONFIG_COMMANDS
from .debug import COMMANDS as DEBUG_COMMANDS
from .donar import COMMANDS as DONAR_COMMANDS
from .gastos import COMMANDS as GASTOS_COMMANDS
from .galerazas import COMMANDS as GALERAZAS_COMMANDS
from .help import COMMANDS as HELP_COMMANDS
from .hola import COMMANDS as HOLA_COMMANDS
from .hisopos import COMMANDS as HISOPOS_COMMANDS
from .lil import COMMANDS as LIL_COMMANDS
from .nivel import COMMANDS as NIVEL_COMMANDS
from .novedad import COMMANDS as NOVEDAD_COMMANDS
from .reportar import COMMANDS as REPORTAR_COMMANDS
from .regalar_hisopo import COMMANDS as GIFT_HISOPO_COMMANDS
from .reiniciarbot import COMMANDS as RESTART_COMMANDS
from .restrictions import COMMANDS as RESTRICTIONS_COMMANDS
from .ruletarusa import COMMANDS as RUSSIAN_ROULETTE_COMMANDS
from .salir import COMMANDS as SALIR_COMMANDS
from .start import COMMANDS as START_COMMANDS
from .triggers import COMMANDS as TRIGGERS_COMMANDS
from .version import COMMANDS as VERSION_COMMANDS


COMMANDS: dict[str, Command] = {
    **SHUTDOWN_COMMANDS,
    **ANUNCIO_COMMANDS,
    **HELP_COMMANDS,
    **START_COMMANDS,
    **HOLA_COMMANDS,
    **LIL_COMMANDS,
    **NIVEL_COMMANDS,
    **BLACKLIST_COMMANDS,
    **NOVEDAD_COMMANDS,
    **REPORTAR_COMMANDS,
    **GIFT_HISOPO_COMMANDS,
    **RESTART_COMMANDS,
    **RESTRICTIONS_COMMANDS,
    **RUSSIAN_ROULETTE_COMMANDS,
    **BACKUP_COMMANDS,
    **DEBUG_COMMANDS,
    **DONAR_COMMANDS,
    **GASTOS_COMMANDS,
    **CHATS_COMMANDS,
    **CONFIG_COMMANDS,
    **GALERAZAS_COMMANDS,
    **HISOPOS_COMMANDS,
    **TRIGGERS_COMMANDS,
    **VERSION_COMMANDS,
    **SALIR_COMMANDS,
}
