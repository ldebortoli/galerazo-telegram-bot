from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .i18n import t
from .language_catalogs import LANGUAGE_NAMES, LANGUAGE_OPTIONS


CONFIG_PREFIX = "config"
LANGUAGES_PER_ROW = 2
LANGUAGES_PER_PAGE = 12


@dataclass(frozen=True)
class LanguageOption:
    code: str
    label: str


@dataclass(frozen=True)
class CommandGroupOption:
    key: str
    label: str


LANGUAGES = tuple(LanguageOption(option["code"], option["native"]) for option in LANGUAGE_OPTIONS)
LANGUAGE_MENU_REVISION = sha256(repr(LANGUAGE_OPTIONS).encode()).hexdigest()[:8]
_LANGUAGE_METADATA = {option["code"]: option for option in LANGUAGE_OPTIONS}
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


def language_page_count() -> int:
    return (len(LANGUAGES) + LANGUAGES_PER_PAGE - 1) // LANGUAGES_PER_PAGE


def selected_language_page(current_language: str) -> int:
    return next((i // LANGUAGES_PER_PAGE for i, option in enumerate(LANGUAGES) if option.code == current_language), 0)


def parse_language_action(parsed: tuple[str, ...], current_language: str) -> tuple[int, str | None] | None:
    if parsed == ("language",):
        return selected_language_page(current_language), None
    if not ((parsed[0] == "langpage" and len(parsed) == 4) or (parsed[0] == "lang" and len(parsed) == 5)):
        return None
    page_text, previous_language, revision = parsed[-3:]
    if previous_language != current_language or revision != LANGUAGE_MENU_REVISION:
        return None
    if not page_text.isascii() or not page_text.isdecimal() or len(page_text) > 3:
        return None
    page = int(page_text)
    if page >= language_page_count():
        return None
    selected = parsed[1] if parsed[0] == "lang" else None
    if selected is not None and selected not in {option.code for option in LANGUAGES[page * LANGUAGES_PER_PAGE:(page + 1) * LANGUAGES_PER_PAGE]}:
        return None
    return page, selected


def language_menu_text(language: str) -> str:
    text = t(language, "config.language")
    if _LANGUAGE_METADATA.get(language, _LANGUAGE_METADATA["es"])["machine"]:
        text += "\n\n" + t(language, "config.translation_notice")
    return text


def build_language_menu(current_language: str, page: int | None = None) -> InlineKeyboardMarkup:
    if page is None:
        page = selected_language_page(current_language)
    if type(page) is not int or not 0 <= page < language_page_count():
        raise ValueError("Invalid language page")
    names = LANGUAGE_NAMES.get(current_language, LANGUAGE_NAMES["es"])
    state = f"{page}:{current_language}:{LANGUAGE_MENU_REVISION}"
    buttons = [
        InlineKeyboardButton(
            _selected_label(f"\u2068{language.label}\u2069 (\u2068{names[language.code]}\u2069)", language.code == current_language),
            callback_data=f"{CONFIG_PREFIX}:lang:{language.code}:{state}",
        )
        for language in LANGUAGES[page * LANGUAGES_PER_PAGE:(page + 1) * LANGUAGES_PER_PAGE]
    ]
    rows = [buttons[index : index + LANGUAGES_PER_ROW] for index in range(0, len(buttons), LANGUAGES_PER_ROW)]
    rtl = _LANGUAGE_METADATA.get(current_language, _LANGUAGE_METADATA["es"])["direction"] == "rtl"
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(f"{'→' if rtl else '←'} {t(current_language, 'config.previous_page')}", callback_data=f"{CONFIG_PREFIX}:langpage:{page - 1}:{current_language}:{LANGUAGE_MENU_REVISION}"))
    navigation.append(InlineKeyboardButton(t(current_language, "config.language_page", page=page + 1, pages=language_page_count()), callback_data=f"{CONFIG_PREFIX}:langinfo"))
    if page + 1 < language_page_count():
        navigation.append(InlineKeyboardButton(f"{t(current_language, 'config.next_page')} {'←' if rtl else '→'}", callback_data=f"{CONFIG_PREFIX}:langpage:{page + 1}:{current_language}:{LANGUAGE_MENU_REVISION}"))
    rows.append(navigation)
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
