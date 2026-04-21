from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


CONFIG_PREFIX = "config"


@dataclass(frozen=True)
class LanguageOption:
    code: str
    label: str


@dataclass(frozen=True)
class CommandGroupOption:
    key: str
    label: str


LANGUAGES = (LanguageOption("es", "Español"),)
COMMAND_GROUPS = (CommandGroupOption("galeraza", "Galeraza"),)


def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Idioma", callback_data=f"{CONFIG_PREFIX}:language")],
            [InlineKeyboardButton("Comandos", callback_data=f"{CONFIG_PREFIX}:commands")],
        ]
    )


def build_language_menu(current_language: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                _selected_label(language.label, language.code == current_language),
                callback_data=f"{CONFIG_PREFIX}:lang:{language.code}",
            )
        ]
        for language in LANGUAGES
    ]
    rows.append([_back_button(f"{CONFIG_PREFIX}:main")])
    return InlineKeyboardMarkup(rows)


def build_command_groups_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(group.label, callback_data=f"{CONFIG_PREFIX}:command:{group.key}")]
        for group in COMMAND_GROUPS
    ]
    rows.append([_back_button(f"{CONFIG_PREFIX}:main")])
    return InlineKeyboardMarkup(rows)


def build_command_group_menu(command_group: str, enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _selected_label("Sí", enabled),
                    callback_data=f"{CONFIG_PREFIX}:set:{command_group}:1",
                ),
                InlineKeyboardButton(
                    _selected_label("No", not enabled),
                    callback_data=f"{CONFIG_PREFIX}:set:{command_group}:0",
                ),
            ],
            [_back_button(f"{CONFIG_PREFIX}:commands")],
        ]
    )


def command_group_label(command_group: str) -> str:
    for group in COMMAND_GROUPS:
        if group.key == command_group:
            return group.label
    return command_group


def is_valid_language(language: str) -> bool:
    return any(option.code == language for option in LANGUAGES)


def is_valid_command_group(command_group: str) -> bool:
    return any(group.key == command_group for group in COMMAND_GROUPS)


def parse_config_callback(data: str) -> tuple[str, ...] | None:
    parts = tuple(data.split(":"))
    if len(parts) < 2 or parts[0] != CONFIG_PREFIX:
        return None
    return parts[1:]


def _back_button(callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("< Atrás", callback_data=callback_data)


def _selected_label(label: str, selected: bool) -> str:
    return f"[ {label} ]" if selected else label
