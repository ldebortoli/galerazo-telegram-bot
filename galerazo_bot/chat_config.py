from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .i18n import t


CONFIG_PREFIX = "config"
LANGUAGES_PER_ROW = 4


@dataclass(frozen=True)
class LanguageOption:
    code: str
    label: str


@dataclass(frozen=True)
class CommandGroupOption:
    key: str
    label: str


LANGUAGES = (
    LanguageOption("es", "Espa\u00f1ol"),
    LanguageOption("es_ES", "Espa\u00f1ol (Espa\u00f1a)"),
    LanguageOption("en", "English"),
    LanguageOption("ru", "\u0420\u0443\u0441\u0441\u043a\u0438\u0439"),
    LanguageOption("la", "Latine"),
    LanguageOption("ja", "\u65e5\u672c\u8a9e"),
    LanguageOption("it", "Italiano"),
    LanguageOption("fr", "Fran\u00e7ais"),
    LanguageOption("de", "Deutsch"),
    LanguageOption("nl", "Nederlands"),
    LanguageOption("zh_Hans", "\u4e2d\u6587 (\u7b80\u4f53)"),
    LanguageOption("zh_Hant", "\u4e2d\u6587 (\u7e41\u9ad4)"),
    LanguageOption("pt_BR", "Portugu\u00eas (Brasil)"),
    LanguageOption("pt_PT", "Portugu\u00eas (Portugal)"),
    LanguageOption("ca", "Catal\u00e0"),
    LanguageOption("eu", "Euskara"),
    LanguageOption("gn", "Ava\u00f1e'\u1ebd"),
    LanguageOption("quz", "Runa Simi"),
)
COMMAND_GROUPS = (
    CommandGroupOption("galeraza", "Galeraza"),
    CommandGroupOption("hisopos", "Recolector de Hisopos"),
    CommandGroupOption("triggers", "Triggers"),
    CommandGroupOption("ruletarusa", "Ruleta rusa"),
)


def build_main_menu(language: str, include_command_groups: bool = True) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(t(language, "config.language"), callback_data=f"{CONFIG_PREFIX}:language")]]
    rows.append([InlineKeyboardButton(t(language, "config.announcements"), callback_data=f"{CONFIG_PREFIX}:announcements")])
    if include_command_groups:
        rows.append([InlineKeyboardButton(t(language, "config.commands"), callback_data=f"{CONFIG_PREFIX}:commands")])
    rows.append([_close_button()])
    return InlineKeyboardMarkup(rows)


def build_language_menu(current_language: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            _selected_label(language.label, language.code == current_language),
            callback_data=f"{CONFIG_PREFIX}:lang:{language.code}",
        )
        for language in LANGUAGES
    ]
    rows = [buttons[index : index + LANGUAGES_PER_ROW] for index in range(0, len(buttons), LANGUAGES_PER_ROW)]
    rows.append(_navigation_row(current_language, f"{CONFIG_PREFIX}:main"))
    return InlineKeyboardMarkup(rows)


def build_announcements_menu(enabled: bool, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _selected_label(t(language, "config.yes"), enabled),
                    callback_data=f"{CONFIG_PREFIX}:setannouncements:1",
                ),
                InlineKeyboardButton(
                    _selected_label(t(language, "config.no"), not enabled),
                    callback_data=f"{CONFIG_PREFIX}:setannouncements:0",
                ),
            ],
            _navigation_row(language, f"{CONFIG_PREFIX}:main"),
        ]
    )


def build_command_groups_menu(language: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(command_group_label(group.key, language), callback_data=f"{CONFIG_PREFIX}:command:{group.key}")]
        for group in COMMAND_GROUPS
    ]
    rows.append(_navigation_row(language, f"{CONFIG_PREFIX}:main"))
    return InlineKeyboardMarkup(rows)


def build_command_group_menu(command_group: str, enabled: bool, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _selected_label(t(language, "config.yes"), enabled),
                    callback_data=f"{CONFIG_PREFIX}:set:{command_group}:1",
                ),
                InlineKeyboardButton(
                    _selected_label(t(language, "config.no"), not enabled),
                    callback_data=f"{CONFIG_PREFIX}:set:{command_group}:0",
                ),
            ],
            _navigation_row(language, f"{CONFIG_PREFIX}:commands"),
        ]
    )


def build_hisopo_menu(enabled: bool, intensity_percent: int, language: str) -> InlineKeyboardMarkup:
    intensity_buttons = [
        InlineKeyboardButton(
            _selected_label(
                f"{t(language, f'hisopos.intensity.{key}')} ({percent}%)",
                intensity_percent == percent,
            ),
            callback_data=f"{CONFIG_PREFIX}:intensity:{percent}",
        )
        for key, percent in (
            ("very_low", 1),
            ("low", 5),
            ("medium", 10),
            ("high", 15),
            ("very_high", 20),
        )
    ]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _selected_label(t(language, "config.yes"), enabled),
                    callback_data=f"{CONFIG_PREFIX}:set:hisopos:1",
                ),
                InlineKeyboardButton(
                    _selected_label(t(language, "config.no"), not enabled),
                    callback_data=f"{CONFIG_PREFIX}:set:hisopos:0",
                ),
            ],
            *[
                intensity_buttons[index : index + 2]
                for index in range(0, len(intensity_buttons), 2)
            ],
            _navigation_row(language, f"{CONFIG_PREFIX}:commands"),
        ]
    )


def command_group_label(command_group: str, language: str) -> str:
    translation_key = f"config.command_group.{command_group}"
    translated = t(language, translation_key)
    if translated != translation_key:
        return translated
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


def _back_button(language: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(t(language, "config.back"), callback_data=callback_data)


def _close_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("\u274c", callback_data=f"{CONFIG_PREFIX}:close")


def _navigation_row(language: str, back_callback_data: str) -> list[InlineKeyboardButton]:
    return [_back_button(language, back_callback_data), _close_button()]


def _selected_label(label: str, selected: bool) -> str:
    return f"[ {label} ]" if selected else label
