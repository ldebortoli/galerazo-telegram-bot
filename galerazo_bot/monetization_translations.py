from __future__ import annotations


_ENGLISH = {
    "help.donantes": "shows the top supporters",
    "help.paysupport": "shows help for payments",
    "help.terminos": "shows purchase and membership terms",
    "donation.not_configured": "The Stars donation menu is not configured.",
    "donation.send_failed": "I could not open the support menu. Please try again later.",
    "donation.open_mini_app": "Open Hisopo collection",
    "donation.menu": (
        "Support Galerazo Bot\n\n"
        "Choose a voluntary Telegram Stars contribution or join the Club del Hisopo. "
        "Donations and membership never add points or improve odds. Each button is created for the person who used /donar."
    ),
    "hisopos.collection.open_app": "Open interactive album",
    "donors.public": "Your name may now appear next to your confirmed donations.",
    "donors.anonymous": "Your confirmed donations will be shown anonymously.",
    "donors.empty": "There are no confirmed Stars donations yet.",
    "donors.header": "Top supporters (confirmed donations only):",
    "donors.hidden_name": "Anonymous",
    "donors.privacy_hint": "Use /donantes public or /donantes anonymous to choose how your name is displayed.",
    "payments.support": (
        "Payment support\n"
        "Send /reportar with the approximate date, Stars amount and what you tried to buy. "
        "Never send passwords, two-factor codes, recovery phrases or full wallet credentials."
    ),
    "payments.terms": (
        "Stars purchases and Club del Hisopo\n"
        "Paid Hisopos are cosmetic and give no points or advantage. Club del Hisopo is a support membership that renews every 30 days for the price shown before payment; it does not grant Hisopos, points or advantages. "
        "Cancelling stops future renewals. Approved refunds subtract donations from the ranking, remove an associated purchased item when applicable and adjust the refunded membership period. Telegram's Stars terms also apply: https://telegram.org/tos/stars"
    ),
}

_SPANISH = {
    "help.donantes": "muestra el top de colaboradores",
    "help.paysupport": "muestra la ayuda para pagos",
    "help.terminos": "muestra las condiciones de compras y membresía",
    "donation.not_configured": "El menú de aportes con Stars no está configurado.",
    "donation.send_failed": "No pude abrir el menú de apoyo. Probá de nuevo más tarde.",
    "donation.open_mini_app": "Abrir colección de Hisopos",
    "donation.menu": (
        "Apoyá a Galerazo Bot\n\n"
        "Elegí un aporte voluntario con Telegram Stars o sumate al Club del Hisopo. "
        "Las donaciones y la membresía nunca suman puntos ni mejoran probabilidades. Cada botón se crea para quien usó /donar."
    ),
    "hisopos.collection.open_app": "Abrir álbum interactivo",
    "donors.public": "Tu nombre ahora puede aparecer junto a tus aportes confirmados.",
    "donors.anonymous": "Tus aportes confirmados se mostrarán de forma anónima.",
    "donors.empty": "Todavía no hay aportes confirmados con Stars.",
    "donors.header": "Top colaboradores (solo donaciones confirmadas):",
    "donors.hidden_name": "Anónimo",
    "donors.privacy_hint": "Usá /donantes publico o /donantes anonimo para elegir cómo se muestra tu nombre.",
    "payments.support": (
        "Soporte de pagos\n"
        "Enviá /reportar con la fecha aproximada, el importe en Stars y qué intentaste comprar. "
        "Nunca envíes contraseñas, códigos de dos pasos, frases de recuperación ni credenciales completas de billeteras."
    ),
    "payments.terms": (
        "Compras con Stars y Club del Hisopo\n"
        "Los Hisopos pagos son cosméticos y no dan puntos ni ventajas. El Club del Hisopo es una membresía de apoyo que se renueva cada 30 días por el precio mostrado antes de pagar; no entrega Hisopos, puntos ni ventajas. "
        "Cancelar detiene cobros futuros. Un reembolso aprobado descuenta la donación del ranking, retira el artículo comprado cuando corresponde y ajusta el período de membresía reembolsado. También rigen los términos de Stars de Telegram: https://telegram.org/tos/stars"
    ),
}

_LANGUAGES = (
    "es",
    "en",
    "ca",
    "de",
    "es_ES",
    "eu",
    "fr",
    "gn",
    "it",
    "ja",
    "la",
    "nl",
    "pt_BR",
    "pt_PT",
    "quz",
    "ru",
    "zh_Hans",
    "zh_Hant",
)

MONETIZATION_TRANSLATIONS = {language: dict(_ENGLISH) for language in _LANGUAGES}
MONETIZATION_TRANSLATIONS["es"] = dict(_SPANISH)
MONETIZATION_TRANSLATIONS["es_ES"] = dict(_SPANISH)
