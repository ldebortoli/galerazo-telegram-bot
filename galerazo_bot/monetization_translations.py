from __future__ import annotations


_ENGLISH = {
    "help.donantes": "shows the top supporters",
    "help.paysupport": "shows help for payments",
    "help.terminos": "shows purchase and membership terms",
    "donation.not_configured": "The Stars donation menu is not configured.",
    "donation.send_failed": "I could not open the support menu. Please try again later.",
    "donation.open_mini_app": "Open Hisopo collection",
    "donation.menu": (
        "Choose a monetary contribution with Telegram Stars, join the Club del Hisopo, "
        "or donate your grandma's pension."
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
        "Paid Hisopos are cosmetic and give no points or advantage. Club del Hisopo costs 100 Stars every 30 days. It grants one permanent Estelar after each 90 consecutive paid days, first at day 90, never when paying the third period in advance. "
        "Cancelling stops future renewals; already paid time still counts. A gap after expiry resets unfinished progress; earned Estelares remain. Refunds remove the refunded time and any Club rewards it no longer supports, without removing gifted or legacy Estelares. Approved refunds also subtract donations from the ranking or remove the associated purchased item. Telegram's Stars terms apply: https://telegram.org/tos/stars"
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
        "Elegí un aporte monetario con Telegram Stars, sumate al Club del Hisopo o "
        "doname la jubilación de tu abuela."
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
        "Los Hisopos pagos son cosméticos y no dan puntos ni ventajas. El Club del Hisopo cuesta 100 Stars cada 30 días. Entrega un Estelar permanente al completar cada 90 días consecutivos pagos, el primero recién al día 90, nunca al pagar la tercera cuota por adelantado. "
        "Cancelar detiene cobros futuros; el tiempo ya pagado sigue contando. Si vence y hay una interrupción, el progreso incompleto empieza de cero; los Estelares ganados se conservan. Un reembolso descuenta ese tiempo y los premios del Club que dejen de corresponder, sin quitar Estelares regalados o históricos. También descuenta donaciones del ranking o retira el artículo comprado cuando corresponde. Rigen los términos de Stars de Telegram: https://telegram.org/tos/stars"
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
