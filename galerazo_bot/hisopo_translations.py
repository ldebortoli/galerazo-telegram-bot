from __future__ import annotations

from html import escape
import re


HISOPO_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "help.hisopos": "muestra la tabla del Recolector de Hisopos",
        "config.command_group.hisopos": "Recolector de Hisopos",
        "hisopos.group_only": "El Recolector de Hisopos solo funciona en grupos y supergrupos.",
        "hisopos.not_configured": "No hay un mecanismo configurado para mostrar la tabla de Hisopos.",
        "hisopos.send_failed": "No pude mostrar la tabla de Hisopos.",
        "hisopos.header": "Tabla de Hisopos",
        "hisopos.empty": "Nadie capturó Hisopos hasta ahora.",
        "hisopos.intensity.title": "Intensidad de apariciones",
        "hisopos.intensity.very_low": "Muy poca",
        "hisopos.intensity.low": "Poca",
        "hisopos.intensity.medium": "Media",
        "hisopos.intensity.high": "Alta",
        "hisopos.intensity.very_high": "Muy alta",
        "hisopos.appeared": "¡Apareció un nuevo hisopo!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Capturar hisopo",
        "hisopos.captured_caption": "{user} capturó un {type_label} y sumó {points} pt.",
        "hisopos.captured_popup": "¡Hisopo capturado! Sumaste {points} pt.",
        "hisopos.taken_alert": "Uh, qué mala suerte, se te adelantaron.",
        "hisopos.rotten_caption": "Este {type_label} se pudrió. Ya no se puede capturar.",
        "hisopos.rotten_alert": "Uh, se pudrió el hisopo. Ya no suma puntos.",
        "hisopos.unavailable_alert": "Este hisopo ya no está disponible.",
        "hisopos.type.common": "hisopo común",
        "hisopos.type.silver": "hisopo plateado",
        "hisopos.type.gold": "hisopo dorado",
    },
    "en": {
        "help.hisopos": "shows the Swab Collector leaderboard",
        "config.command_group.hisopos": "Swab Collector",
        "hisopos.group_only": "Swab Collector only works in groups and supergroups.",
        "hisopos.not_configured": "No mechanism is configured to show the Swab leaderboard.",
        "hisopos.send_failed": "I could not show the Swab leaderboard.",
        "hisopos.header": "Swab Leaderboard",
        "hisopos.empty": "Nobody has captured any Swabs yet.",
        "hisopos.intensity.title": "Appearance intensity",
        "hisopos.intensity.very_low": "Very low",
        "hisopos.intensity.low": "Low",
        "hisopos.intensity.medium": "Medium",
        "hisopos.intensity.high": "High",
        "hisopos.intensity.very_high": "Very high",
        "hisopos.appeared": "A new swab appeared!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Capture swab",
        "hisopos.captured_caption": "{user} captured a {type_label} and earned {points} pt.",
        "hisopos.captured_popup": "Swab captured! You earned {points} pt.",
        "hisopos.taken_alert": "Aw, bad luck. Someone beat you to it.",
        "hisopos.rotten_caption": "This {type_label} went bad. It can no longer be captured.",
        "hisopos.rotten_alert": "Aw, the swab went bad. It is no longer worth points.",
        "hisopos.unavailable_alert": "This swab is no longer available.",
        "hisopos.type.common": "common swab",
        "hisopos.type.silver": "silver swab",
        "hisopos.type.gold": "golden swab",
    },
    "es_ES": {
        "help.hisopos": "muestra la tabla del Recolector de Hisopos",
        "config.command_group.hisopos": "Recolector de Hisopos",
        "hisopos.group_only": "El Recolector de Hisopos solo funciona en grupos y supergrupos.",
        "hisopos.not_configured": "No hay un mecanismo configurado para mostrar la tabla de Hisopos.",
        "hisopos.send_failed": "No pude mostrar la tabla de Hisopos.",
        "hisopos.header": "Tabla de Hisopos",
        "hisopos.empty": "Nadie ha capturado Hisopos todavía.",
        "hisopos.intensity.title": "Intensidad de apariciones",
        "hisopos.intensity.very_low": "Muy poca",
        "hisopos.intensity.low": "Poca",
        "hisopos.intensity.medium": "Media",
        "hisopos.intensity.high": "Alta",
        "hisopos.intensity.very_high": "Muy alta",
        "hisopos.appeared": "¡Ha aparecido un nuevo hisopo!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Capturar hisopo",
        "hisopos.captured_caption": "{user} ha capturado un {type_label} y ha sumado {points} pt.",
        "hisopos.captured_popup": "¡Hisopo capturado! Has sumado {points} pt.",
        "hisopos.taken_alert": "Qué mala suerte, alguien se te ha adelantado.",
        "hisopos.rotten_caption": "Este {type_label} se ha estropeado. Ya no se puede capturar.",
        "hisopos.rotten_alert": "El hisopo se ha estropeado. Ya no suma puntos.",
        "hisopos.unavailable_alert": "Este hisopo ya no está disponible.",
        "hisopos.type.common": "hisopo común",
        "hisopos.type.silver": "hisopo plateado",
        "hisopos.type.gold": "hisopo dorado",
    },
    "ca": {
        "help.hisopos": "mostra la taula del Recol·lector de Bastonets",
        "config.command_group.hisopos": "Recol·lector de Bastonets",
        "hisopos.group_only": "El Recol·lector de Bastonets només funciona en grups i supergrups.",
        "hisopos.not_configured": "No hi ha cap mecanisme configurat per mostrar la taula de Bastonets.",
        "hisopos.send_failed": "No he pogut mostrar la taula de Bastonets.",
        "hisopos.header": "Taula de Bastonets",
        "hisopos.empty": "Encara ningú no ha capturat Bastonets.",
        "hisopos.intensity.title": "Intensitat d'aparició",
        "hisopos.intensity.very_low": "Molt baixa",
        "hisopos.intensity.low": "Baixa",
        "hisopos.intensity.medium": "Mitjana",
        "hisopos.intensity.high": "Alta",
        "hisopos.intensity.very_high": "Molt alta",
        "hisopos.appeared": "Ha aparegut un bastonet nou!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Captura el bastonet",
        "hisopos.captured_caption": "{user} ha capturat un {type_label} i ha sumat {points} pt.",
        "hisopos.captured_popup": "Bastonet capturat! Has sumat {points} pt.",
        "hisopos.taken_alert": "Quina mala sort, algú se t'ha avançat.",
        "hisopos.rotten_caption": "Aquest {type_label} s'ha fet malbé. Ja no es pot capturar.",
        "hisopos.rotten_alert": "El bastonet s'ha fet malbé. Ja no val punts.",
        "hisopos.unavailable_alert": "Aquest bastonet ja no està disponible.",
        "hisopos.type.common": "bastonet comú",
        "hisopos.type.silver": "bastonet platejat",
        "hisopos.type.gold": "bastonet daurat",
    },
    "de": {
        "help.hisopos": "zeigt die Rangliste des Wattestäbchen-Sammlers",
        "config.command_group.hisopos": "Wattestäbchen-Sammler",
        "hisopos.group_only": "Der Wattestäbchen-Sammler funktioniert nur in Gruppen und Supergruppen.",
        "hisopos.not_configured": "Es ist kein Mechanismus für die Wattestäbchen-Rangliste konfiguriert.",
        "hisopos.send_failed": "Ich konnte die Wattestäbchen-Rangliste nicht anzeigen.",
        "hisopos.header": "Wattestäbchen-Rangliste",
        "hisopos.empty": "Noch hat niemand Wattestäbchen gefangen.",
        "hisopos.intensity.title": "Erscheinungshäufigkeit",
        "hisopos.intensity.very_low": "Sehr niedrig",
        "hisopos.intensity.low": "Niedrig",
        "hisopos.intensity.medium": "Mittel",
        "hisopos.intensity.high": "Hoch",
        "hisopos.intensity.very_high": "Sehr hoch",
        "hisopos.appeared": "Ein neues Wattestäbchen ist erschienen!\n{type_label} · {points} Pt.",
        "hisopos.capture_button": "Wattestäbchen fangen",
        "hisopos.captured_caption": "{user} hat ein {type_label} gefangen und {points} Pt. erhalten.",
        "hisopos.captured_popup": "Wattestäbchen gefangen! Du erhältst {points} Pt.",
        "hisopos.taken_alert": "Pech gehabt, jemand war schneller.",
        "hisopos.rotten_caption": "Dieses {type_label} ist verdorben und kann nicht mehr gefangen werden.",
        "hisopos.rotten_alert": "Das Wattestäbchen ist verdorben und keine Punkte mehr wert.",
        "hisopos.unavailable_alert": "Dieses Wattestäbchen ist nicht mehr verfügbar.",
        "hisopos.type.common": "gewöhnliches Wattestäbchen",
        "hisopos.type.silver": "silbernes Wattestäbchen",
        "hisopos.type.gold": "goldenes Wattestäbchen",
    },
    "eu": {
        "help.hisopos": "Kotoi Biltzailearen sailkapena erakusten du",
        "config.command_group.hisopos": "Kotoi Biltzailea",
        "hisopos.group_only": "Kotoi Biltzaileak talde eta supertaldeetan bakarrik funtzionatzen du.",
        "hisopos.not_configured": "Ez dago Kotoien sailkapena erakusteko mekanismorik konfiguratuta.",
        "hisopos.send_failed": "Ezin izan dut Kotoien sailkapena erakutsi.",
        "hisopos.header": "Kotoien Sailkapena",
        "hisopos.empty": "Oraindik inork ez du Kotoirik harrapatu.",
        "hisopos.intensity.title": "Agertze-intentsitatea",
        "hisopos.intensity.very_low": "Oso txikia",
        "hisopos.intensity.low": "Txikia",
        "hisopos.intensity.medium": "Ertaina",
        "hisopos.intensity.high": "Handia",
        "hisopos.intensity.very_high": "Oso handia",
        "hisopos.appeared": "Kotoi berri bat agertu da!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Kotoia harrapatu",
        "hisopos.captured_caption": "{user}(e)k {type_label} bat harrapatu eta {points} pt lortu ditu.",
        "hisopos.captured_popup": "Kotoia harrapatuta! {points} pt lortu dituzu.",
        "hisopos.taken_alert": "Zorte txarra, norbait aurreratu zaizu.",
        "hisopos.rotten_caption": "{type_label} hau usteldu da. Ezin da gehiago harrapatu.",
        "hisopos.rotten_alert": "Kotoia usteldu da. Ez du punturik ematen.",
        "hisopos.unavailable_alert": "Kotoi hau jada ez dago erabilgarri.",
        "hisopos.type.common": "kotoi arrunta",
        "hisopos.type.silver": "zilarrezko kotoia",
        "hisopos.type.gold": "urrezko kotoia",
    },
    "fr": {
        "help.hisopos": "affiche le classement du Collectionneur de Cotons-tiges",
        "config.command_group.hisopos": "Collectionneur de Cotons-tiges",
        "hisopos.group_only": "Le Collectionneur de Cotons-tiges fonctionne uniquement dans les groupes et supergroupes.",
        "hisopos.not_configured": "Aucun mécanisme n'est configuré pour afficher le classement des Cotons-tiges.",
        "hisopos.send_failed": "Je n'ai pas pu afficher le classement des Cotons-tiges.",
        "hisopos.header": "Classement des Cotons-tiges",
        "hisopos.empty": "Personne n'a encore capturé de Cotons-tiges.",
        "hisopos.intensity.title": "Intensité d'apparition",
        "hisopos.intensity.very_low": "Très faible",
        "hisopos.intensity.low": "Faible",
        "hisopos.intensity.medium": "Moyenne",
        "hisopos.intensity.high": "Élevée",
        "hisopos.intensity.very_high": "Très élevée",
        "hisopos.appeared": "Un nouveau coton-tige est apparu !\n{type_label} · {points} pt",
        "hisopos.capture_button": "Capturer le coton-tige",
        "hisopos.captured_caption": "{user} a capturé un {type_label} et gagné {points} pt.",
        "hisopos.captured_popup": "Coton-tige capturé ! Vous gagnez {points} pt.",
        "hisopos.taken_alert": "Pas de chance, quelqu'un vous a devancé.",
        "hisopos.rotten_caption": "Ce {type_label} a pourri. Il ne peut plus être capturé.",
        "hisopos.rotten_alert": "Le coton-tige a pourri. Il ne rapporte plus de points.",
        "hisopos.unavailable_alert": "Ce coton-tige n'est plus disponible.",
        "hisopos.type.common": "coton-tige ordinaire",
        "hisopos.type.silver": "coton-tige argenté",
        "hisopos.type.gold": "coton-tige doré",
    },
    "gn": {
        "help.hisopos": "ohechauka Hisopo Ñembyatýha rechaukaha",
        "config.command_group.hisopos": "Hisopo Ñembyatýha",
        "hisopos.group_only": "Hisopo Ñembyatýha omba'apo aty ha atyguasupe añónte.",
        "hisopos.not_configured": "Ndaipóri tape oñembohekopyréva Hisopo rechaukaha ojehechauka hag̃ua.",
        "hisopos.send_failed": "Ndaikatúi ahechauka Hisopo rechaukaha.",
        "hisopos.header": "Hisopo Rechaukaha",
        "hisopos.empty": "Avave ne'ĩra ojapyhy Hisopo.",
        "hisopos.intensity.title": "Mba'éichapa py'ỹi osẽ",
        "hisopos.intensity.very_low": "Sa'ieterei",
        "hisopos.intensity.low": "Sa'i",
        "hisopos.intensity.medium": "Mbyte",
        "hisopos.intensity.high": "Heta",
        "hisopos.intensity.very_high": "Hetaiterei",
        "hisopos.appeared": "Peteĩ hisopo pyahu osẽ!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Hisopo japyhy",
        "hisopos.captured_caption": "{user} ojapyhy peteĩ {type_label} ha ohupyty {points} pt.",
        "hisopos.captured_popup": "Hisopo ojejapyhýma! Rehupyty {points} pt.",
        "hisopos.taken_alert": "Naiporãi nde suerte, ambue tenonde ndehegui.",
        "hisopos.rotten_caption": "Ko {type_label} oñembyai. Ndaikatúi ojejapyhyvéima.",
        "hisopos.rotten_alert": "Hisopo oñembyai. Nome'ẽvéima punto.",
        "hisopos.unavailable_alert": "Ko hisopo ndaiporivéima.",
        "hisopos.type.common": "hisopo jepivegua",
        "hisopos.type.silver": "hisopo plata",
        "hisopos.type.gold": "hisopo óro",
    },
    "it": {
        "help.hisopos": "mostra la classifica del Raccoglitore di Cotton Fioc",
        "config.command_group.hisopos": "Raccoglitore di Cotton Fioc",
        "hisopos.group_only": "Il Raccoglitore di Cotton Fioc funziona solo nei gruppi e supergruppi.",
        "hisopos.not_configured": "Non è configurato alcun meccanismo per mostrare la classifica dei Cotton Fioc.",
        "hisopos.send_failed": "Non ho potuto mostrare la classifica dei Cotton Fioc.",
        "hisopos.header": "Classifica dei Cotton Fioc",
        "hisopos.empty": "Nessuno ha ancora catturato Cotton Fioc.",
        "hisopos.intensity.title": "Intensità delle apparizioni",
        "hisopos.intensity.very_low": "Molto bassa",
        "hisopos.intensity.low": "Bassa",
        "hisopos.intensity.medium": "Media",
        "hisopos.intensity.high": "Alta",
        "hisopos.intensity.very_high": "Molto alta",
        "hisopos.appeared": "È apparso un nuovo cotton fioc!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Cattura cotton fioc",
        "hisopos.captured_caption": "{user} ha catturato un {type_label} e ottenuto {points} pt.",
        "hisopos.captured_popup": "Cotton fioc catturato! Hai ottenuto {points} pt.",
        "hisopos.taken_alert": "Che sfortuna, qualcuno ti ha preceduto.",
        "hisopos.rotten_caption": "Questo {type_label} è marcito. Non può più essere catturato.",
        "hisopos.rotten_alert": "Il cotton fioc è marcito. Non vale più punti.",
        "hisopos.unavailable_alert": "Questo cotton fioc non è più disponibile.",
        "hisopos.type.common": "cotton fioc comune",
        "hisopos.type.silver": "cotton fioc argentato",
        "hisopos.type.gold": "cotton fioc dorato",
    },
    "ja": {
        "help.hisopos": "綿棒コレクターのランキングを表示します",
        "config.command_group.hisopos": "綿棒コレクター",
        "hisopos.group_only": "綿棒コレクターはグループとスーパーグループでのみ利用できます。",
        "hisopos.not_configured": "綿棒ランキングを表示する仕組みが設定されていません。",
        "hisopos.send_failed": "綿棒ランキングを表示できませんでした。",
        "hisopos.header": "綿棒ランキング",
        "hisopos.empty": "まだ誰も綿棒を捕まえていません。",
        "hisopos.intensity.title": "出現頻度",
        "hisopos.intensity.very_low": "とても低い",
        "hisopos.intensity.low": "低い",
        "hisopos.intensity.medium": "普通",
        "hisopos.intensity.high": "高い",
        "hisopos.intensity.very_high": "とても高い",
        "hisopos.appeared": "新しい綿棒が現れた！\n{type_label} · {points} pt",
        "hisopos.capture_button": "綿棒を捕まえる",
        "hisopos.captured_caption": "{user}が{type_label}を捕まえて{points} ptを獲得しました。",
        "hisopos.captured_popup": "綿棒を捕まえた！{points} pt獲得。",
        "hisopos.taken_alert": "残念、誰かに先を越されました。",
        "hisopos.rotten_caption": "この{type_label}は腐りました。もう捕まえられません。",
        "hisopos.rotten_alert": "綿棒は腐りました。もうポイントになりません。",
        "hisopos.unavailable_alert": "この綿棒はもう利用できません。",
        "hisopos.type.common": "普通の綿棒",
        "hisopos.type.silver": "銀の綿棒",
        "hisopos.type.gold": "金の綿棒",
    },
    "la": {
        "help.hisopos": "tabulam Collectoris Bacillorum ostendit",
        "config.command_group.hisopos": "Collector Bacillorum",
        "hisopos.group_only": "Collector Bacillorum tantum in gregibus et supergregibus operatur.",
        "hisopos.not_configured": "Nulla ratio ad tabulam Bacillorum ostendendam configurata est.",
        "hisopos.send_failed": "Tabulam Bacillorum ostendere non potui.",
        "hisopos.header": "Tabula Bacillorum",
        "hisopos.empty": "Nemo adhuc Bacillum cepit.",
        "hisopos.intensity.title": "Frequentia apparitionum",
        "hisopos.intensity.very_low": "Minima",
        "hisopos.intensity.low": "Parva",
        "hisopos.intensity.medium": "Media",
        "hisopos.intensity.high": "Magna",
        "hisopos.intensity.very_high": "Maxima",
        "hisopos.appeared": "Novum bacillum apparuit!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Bacillum cape",
        "hisopos.captured_caption": "{user} {type_label} cepit et {points} pt accepit.",
        "hisopos.captured_popup": "Bacillum captum! {points} pt accepisti.",
        "hisopos.taken_alert": "O infelicitas, alius te antecessit.",
        "hisopos.rotten_caption": "Hoc {type_label} putruit. Iam capi non potest.",
        "hisopos.rotten_alert": "Bacillum putruit. Iam puncta non valet.",
        "hisopos.unavailable_alert": "Hoc bacillum iam praesto non est.",
        "hisopos.type.common": "bacillum commune",
        "hisopos.type.silver": "bacillum argenteum",
        "hisopos.type.gold": "bacillum aureum",
    },
    "nl": {
        "help.hisopos": "toont het klassement van de Wattenstaafjesverzamelaar",
        "config.command_group.hisopos": "Wattenstaafjesverzamelaar",
        "hisopos.group_only": "De Wattenstaafjesverzamelaar werkt alleen in groepen en supergroepen.",
        "hisopos.not_configured": "Er is geen mechanisme ingesteld om het Wattenstaafjesklassement te tonen.",
        "hisopos.send_failed": "Ik kon het Wattenstaafjesklassement niet tonen.",
        "hisopos.header": "Wattenstaafjesklassement",
        "hisopos.empty": "Nog niemand heeft Wattenstaafjes gevangen.",
        "hisopos.intensity.title": "Verschijningsintensiteit",
        "hisopos.intensity.very_low": "Zeer laag",
        "hisopos.intensity.low": "Laag",
        "hisopos.intensity.medium": "Gemiddeld",
        "hisopos.intensity.high": "Hoog",
        "hisopos.intensity.very_high": "Zeer hoog",
        "hisopos.appeared": "Er is een nieuw wattenstaafje verschenen!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Wattenstaafje vangen",
        "hisopos.captured_caption": "{user} ving een {type_label} en verdiende {points} pt.",
        "hisopos.captured_popup": "Wattenstaafje gevangen! Je verdient {points} pt.",
        "hisopos.taken_alert": "Jammer, iemand was je voor.",
        "hisopos.rotten_caption": "Dit {type_label} is bedorven en kan niet meer worden gevangen.",
        "hisopos.rotten_alert": "Het wattenstaafje is bedorven en geen punten meer waard.",
        "hisopos.unavailable_alert": "Dit wattenstaafje is niet meer beschikbaar.",
        "hisopos.type.common": "gewoon wattenstaafje",
        "hisopos.type.silver": "zilveren wattenstaafje",
        "hisopos.type.gold": "gouden wattenstaafje",
    },
    "pt_BR": {
        "help.hisopos": "mostra o ranking do Coletor de Cotonetes",
        "config.command_group.hisopos": "Coletor de Cotonetes",
        "hisopos.group_only": "O Coletor de Cotonetes só funciona em grupos e supergrupos.",
        "hisopos.not_configured": "Não há mecanismo configurado para mostrar o ranking de Cotonetes.",
        "hisopos.send_failed": "Não consegui mostrar o ranking de Cotonetes.",
        "hisopos.header": "Ranking de Cotonetes",
        "hisopos.empty": "Ninguém capturou Cotonetes ainda.",
        "hisopos.intensity.title": "Intensidade das aparições",
        "hisopos.intensity.very_low": "Muito baixa",
        "hisopos.intensity.low": "Baixa",
        "hisopos.intensity.medium": "Média",
        "hisopos.intensity.high": "Alta",
        "hisopos.intensity.very_high": "Muito alta",
        "hisopos.appeared": "Um novo cotonete apareceu!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Capturar cotonete",
        "hisopos.captured_caption": "{user} capturou um {type_label} e ganhou {points} pt.",
        "hisopos.captured_popup": "Cotonete capturado! Você ganhou {points} pt.",
        "hisopos.taken_alert": "Que azar, alguém chegou primeiro.",
        "hisopos.rotten_caption": "Este {type_label} estragou. Ele não pode mais ser capturado.",
        "hisopos.rotten_alert": "O cotonete estragou. Ele não vale mais pontos.",
        "hisopos.unavailable_alert": "Este cotonete não está mais disponível.",
        "hisopos.type.common": "cotonete comum",
        "hisopos.type.silver": "cotonete prateado",
        "hisopos.type.gold": "cotonete dourado",
    },
    "pt_PT": {
        "help.hisopos": "mostra a classificação do Coletor de Cotonetes",
        "config.command_group.hisopos": "Coletor de Cotonetes",
        "hisopos.group_only": "O Coletor de Cotonetes só funciona em grupos e supergrupos.",
        "hisopos.not_configured": "Não há mecanismo configurado para mostrar a classificação de Cotonetes.",
        "hisopos.send_failed": "Não consegui mostrar a classificação de Cotonetes.",
        "hisopos.header": "Classificação de Cotonetes",
        "hisopos.empty": "Ainda ninguém capturou Cotonetes.",
        "hisopos.intensity.title": "Intensidade das aparições",
        "hisopos.intensity.very_low": "Muito baixa",
        "hisopos.intensity.low": "Baixa",
        "hisopos.intensity.medium": "Média",
        "hisopos.intensity.high": "Alta",
        "hisopos.intensity.very_high": "Muito alta",
        "hisopos.appeared": "Apareceu um novo cotonete!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Capturar cotonete",
        "hisopos.captured_caption": "{user} capturou um {type_label} e ganhou {points} pt.",
        "hisopos.captured_popup": "Cotonete capturado! Ganhou {points} pt.",
        "hisopos.taken_alert": "Que azar, alguém chegou primeiro.",
        "hisopos.rotten_caption": "Este {type_label} estragou-se. Já não pode ser capturado.",
        "hisopos.rotten_alert": "O cotonete estragou-se. Já não vale pontos.",
        "hisopos.unavailable_alert": "Este cotonete já não está disponível.",
        "hisopos.type.common": "cotonete comum",
        "hisopos.type.silver": "cotonete prateado",
        "hisopos.type.gold": "cotonete dourado",
    },
    "quz": {
        "help.hisopos": "Hisopo Huñuqpa yupayninta rikuchin",
        "config.command_group.hisopos": "Hisopo Huñuq",
        "hisopos.group_only": "Hisopo Huñuqqa huñukunallapi, hatun huñukunallapipas llamk'an.",
        "hisopos.not_configured": "Hisopokunap yupayninta rikuchinapaq manam imapas wakichisqachu.",
        "hisopos.send_failed": "Hisopokunap yupayninta manam rikuchiyta atirqanichu.",
        "hisopos.header": "Hisopokunap Yupaynin",
        "hisopos.empty": "Manaraq pipas Hisopota hap'inchu.",
        "hisopos.intensity.title": "Rikhurimuy kallpa",
        "hisopos.intensity.very_low": "Ancha pisi",
        "hisopos.intensity.low": "Pisi",
        "hisopos.intensity.medium": "Chawpi",
        "hisopos.intensity.high": "Achka",
        "hisopos.intensity.very_high": "Ancha achka",
        "hisopos.appeared": "Musuq hisopo rikhurimun!\n{type_label} · {points} pt",
        "hisopos.capture_button": "Hisopota hap'iy",
        "hisopos.captured_caption": "{user}qa {type_label}ta hap'ispa {points} pt chaskirqan.",
        "hisopos.captured_popup": "Hisopo hap'isqa! {points} pt chaskinki.",
        "hisopos.taken_alert": "Mana allin suerte, huk runam ñawpaqta hap'irqan.",
        "hisopos.rotten_caption": "Kay {type_label} ismurun. Manaña hap'iy atikunchu.",
        "hisopos.rotten_alert": "Hisopo ismurun. Manaña puntota qunchu.",
        "hisopos.unavailable_alert": "Kay hisopoqa manaña kanchu.",
        "hisopos.type.common": "sapa kuti hisopo",
        "hisopos.type.silver": "qullqi hisopo",
        "hisopos.type.gold": "quri hisopo",
    },
    "ru": {
        "help.hisopos": "показывает рейтинг Собирателя ватных палочек",
        "config.command_group.hisopos": "Собиратель ватных палочек",
        "hisopos.group_only": "Собиратель ватных палочек работает только в группах и супергруппах.",
        "hisopos.not_configured": "Механизм показа рейтинга ватных палочек не настроен.",
        "hisopos.send_failed": "Не удалось показать рейтинг ватных палочек.",
        "hisopos.header": "Рейтинг ватных палочек",
        "hisopos.empty": "Пока никто не поймал ни одной ватной палочки.",
        "hisopos.intensity.title": "Частота появления",
        "hisopos.intensity.very_low": "Очень низкая",
        "hisopos.intensity.low": "Низкая",
        "hisopos.intensity.medium": "Средняя",
        "hisopos.intensity.high": "Высокая",
        "hisopos.intensity.very_high": "Очень высокая",
        "hisopos.appeared": "Появилась новая ватная палочка!\n{type_label} · {points} оч.",
        "hisopos.capture_button": "Поймать палочку",
        "hisopos.captured_caption": "{user} поймал(а) {type_label} и получил(а) {points} оч.",
        "hisopos.captured_popup": "Палочка поймана! Вы получили {points} оч.",
        "hisopos.taken_alert": "Не повезло: кто-то оказался быстрее.",
        "hisopos.rotten_caption": "Эта {type_label} испортилась. Её больше нельзя поймать.",
        "hisopos.rotten_alert": "Ватная палочка испортилась и больше не приносит очков.",
        "hisopos.unavailable_alert": "Эта ватная палочка больше недоступна.",
        "hisopos.type.common": "обычная ватная палочка",
        "hisopos.type.silver": "серебряная ватная палочка",
        "hisopos.type.gold": "золотая ватная палочка",
    },
    "zh_Hans": {
        "help.hisopos": "显示棉签收集者排行榜",
        "config.command_group.hisopos": "棉签收集者",
        "hisopos.group_only": "棉签收集者仅适用于群组和超级群组。",
        "hisopos.not_configured": "尚未配置显示棉签排行榜的机制。",
        "hisopos.send_failed": "无法显示棉签排行榜。",
        "hisopos.header": "棉签排行榜",
        "hisopos.empty": "目前还没有人捕获棉签。",
        "hisopos.intensity.title": "出现频率",
        "hisopos.intensity.very_low": "非常低",
        "hisopos.intensity.low": "低",
        "hisopos.intensity.medium": "中",
        "hisopos.intensity.high": "高",
        "hisopos.intensity.very_high": "非常高",
        "hisopos.appeared": "出现了一根新棉签！\n{type_label} · {points} 分",
        "hisopos.capture_button": "捕获棉签",
        "hisopos.captured_caption": "{user}捕获了{type_label}，获得{points}分。",
        "hisopos.captured_popup": "棉签已捕获！你获得了{points}分。",
        "hisopos.taken_alert": "运气不好，有人抢先一步。",
        "hisopos.rotten_caption": "这根{type_label}已经腐坏，无法再捕获。",
        "hisopos.rotten_alert": "棉签已经腐坏，不再计分。",
        "hisopos.unavailable_alert": "这根棉签已不可用。",
        "hisopos.type.common": "普通棉签",
        "hisopos.type.silver": "银棉签",
        "hisopos.type.gold": "金棉签",
    },
    "zh_Hant": {
        "help.hisopos": "顯示棉花棒收集者排行榜",
        "config.command_group.hisopos": "棉花棒收集者",
        "hisopos.group_only": "棉花棒收集者僅適用於群組和超級群組。",
        "hisopos.not_configured": "尚未設定顯示棉花棒排行榜的機制。",
        "hisopos.send_failed": "無法顯示棉花棒排行榜。",
        "hisopos.header": "棉花棒排行榜",
        "hisopos.empty": "目前還沒有人捕獲棉花棒。",
        "hisopos.intensity.title": "出現頻率",
        "hisopos.intensity.very_low": "非常低",
        "hisopos.intensity.low": "低",
        "hisopos.intensity.medium": "中",
        "hisopos.intensity.high": "高",
        "hisopos.intensity.very_high": "非常高",
        "hisopos.appeared": "出現了一根新棉花棒！\n{type_label} · {points} 分",
        "hisopos.capture_button": "捕獲棉花棒",
        "hisopos.captured_caption": "{user}捕獲了{type_label}，獲得{points}分。",
        "hisopos.captured_popup": "棉花棒已捕獲！你獲得了{points}分。",
        "hisopos.taken_alert": "運氣不好，有人搶先一步。",
        "hisopos.rotten_caption": "這根{type_label}已經腐壞，無法再捕獲。",
        "hisopos.rotten_alert": "棉花棒已經腐壞，不再計分。",
        "hisopos.unavailable_alert": "這根棉花棒已無法使用。",
        "hisopos.type.common": "普通棉花棒",
        "hisopos.type.silver": "銀棉花棒",
        "hisopos.type.gold": "金棉花棒",
    },
}


HISOPO_SPECIAL_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "hisopos.appeared_mystery": "¡Apareció un nuevo hisopo!\n{type_label} · valor oculto",
        "hisopos.captured_caption_negative": "{user} capturó un {type_label} y perdió {points} pt.",
        "hisopos.captured_popup_negative": "¡Hisopo capturado! Perdiste {points} pt.",
        "hisopos.captured_caption_fake": "{user} iba a capturar un hisopo, ¡pero resultó ser falso! No suma ningún punto.",
        "hisopos.captured_caption_zero": "{user} capturó un {type_label}, pero no sumó ningún punto.",
        "hisopos.captured_popup_zero": "Este hisopo no valía puntos.",
        "hisopos.expired_fleeting_caption": "{user} encontró un {type_label}, pero ya había pasado su minuto fugaz. No sumó puntos.",
        "hisopos.expired_fleeting_popup": "Había un hisopo fugaz, pero se pasó su minuto. No sumaste puntos.",
        "hisopos.type.diamond": "hisopo diamante",
        "hisopos.type.fleeting": "hisopo fugaz",
        "hisopos.type.mystery": "hisopo misterioso",
        "hisopos.type.putrid": "hisopo putrefacto",
        "hisopos.type.radioactive": "hisopo radiactivo",
        "hisopos.type.fake": "hisopo falso",
        "hisopos.type.twin": "hisopo gemelo",
    },
    "en": {
        "hisopos.appeared_mystery": "A new swab appeared!\n{type_label} · hidden value",
        "hisopos.captured_caption_negative": "{user} captured a {type_label} and lost {points} pt.",
        "hisopos.captured_popup_negative": "Swab captured! You lost {points} pt.",
        "hisopos.captured_caption_fake": "{user} was about to capture a swab, but it turned out to be fake! It is worth no points.",
        "hisopos.captured_caption_zero": "{user} captured a {type_label}, but it was worth no points.",
        "hisopos.captured_popup_zero": "This swab was worth no points.",
        "hisopos.expired_fleeting_caption": "{user} found a {type_label}, but its fleeting minute had already passed. No points were awarded.",
        "hisopos.expired_fleeting_popup": "It contained a fleeting swab, but its minute had passed. You earned no points.",
        "hisopos.type.diamond": "diamond swab",
        "hisopos.type.fleeting": "fleeting swab",
        "hisopos.type.mystery": "mystery swab",
        "hisopos.type.putrid": "putrid swab",
        "hisopos.type.radioactive": "radioactive swab",
        "hisopos.type.fake": "fake swab",
        "hisopos.type.twin": "twin swab",
    },
    "es_ES": {
        "hisopos.appeared_mystery": "¡Ha aparecido un nuevo hisopo!\n{type_label} · valor oculto",
        "hisopos.captured_caption_negative": "{user} ha capturado un {type_label} y ha perdido {points} pt.",
        "hisopos.captured_popup_negative": "¡Hisopo capturado! Has perdido {points} pt.",
        "hisopos.captured_caption_fake": "{user} iba a capturar un hisopo, ¡pero resultó ser falso! No suma ningún punto.",
        "hisopos.captured_caption_zero": "{user} ha capturado un {type_label}, pero no ha sumado ningún punto.",
        "hisopos.captured_popup_zero": "Este hisopo no valía puntos.",
        "hisopos.expired_fleeting_caption": "{user} encontró un {type_label}, pero su minuto fugaz ya había pasado. No ha sumado puntos.",
        "hisopos.expired_fleeting_popup": "Había un hisopo fugaz, pero su minuto ya había pasado. No has sumado puntos.",
        "hisopos.type.diamond": "hisopo diamante",
        "hisopos.type.fleeting": "hisopo fugaz",
        "hisopos.type.mystery": "hisopo misterioso",
        "hisopos.type.putrid": "hisopo putrefacto",
        "hisopos.type.radioactive": "hisopo radiactivo",
        "hisopos.type.fake": "hisopo falso",
        "hisopos.type.twin": "hisopo gemelo",
    },
    "ca": {
        "hisopos.appeared_mystery": "Ha aparegut un bastonet nou!\n{type_label} · valor ocult",
        "hisopos.captured_caption_negative": "{user} ha capturat un {type_label} i ha perdut {points} pt.",
        "hisopos.captured_popup_negative": "Bastonet capturat! Has perdut {points} pt.",
        "hisopos.captured_caption_fake": "{user} estava a punt de capturar un bastonet, però ha resultat ser fals! No suma cap punt.",
        "hisopos.captured_caption_zero": "{user} ha capturat un {type_label}, però no ha sumat cap punt.",
        "hisopos.captured_popup_zero": "Aquest bastonet no valia cap punt.",
        "hisopos.expired_fleeting_caption": "{user} ha trobat un {type_label}, però el seu minut fugaç ja havia passat. No ha sumat punts.",
        "hisopos.expired_fleeting_popup": "Hi havia un bastonet fugaç, però el seu minut ja havia passat. No has sumat punts.",
        "hisopos.type.diamond": "bastonet de diamant",
        "hisopos.type.fleeting": "bastonet fugaç",
        "hisopos.type.mystery": "bastonet misteriós",
        "hisopos.type.putrid": "bastonet putrefacte",
        "hisopos.type.radioactive": "bastonet radioactiu",
        "hisopos.type.fake": "bastonet fals",
        "hisopos.type.twin": "bastonet bessó",
    },
    "de": {
        "hisopos.appeared_mystery": "Ein neues Wattestäbchen ist erschienen!\n{type_label} · geheimer Wert",
        "hisopos.captured_caption_negative": "{user} hat ein {type_label} gefangen und {points} Pkt. verloren.",
        "hisopos.captured_popup_negative": "Wattestäbchen gefangen! Du verlierst {points} Pkt.",
        "hisopos.captured_caption_fake": "{user} wollte ein Wattestäbchen fangen, aber es stellte sich als Fälschung heraus! Es gibt keine Punkte.",
        "hisopos.captured_caption_zero": "{user} hat ein {type_label} gefangen, aber keine Punkte erhalten.",
        "hisopos.captured_popup_zero": "Dieses Wattestäbchen war keine Punkte wert.",
        "hisopos.expired_fleeting_caption": "{user} hat ein {type_label} gefunden, aber seine flüchtige Minute war schon vorbei. Es gab keine Punkte.",
        "hisopos.expired_fleeting_popup": "Darin war ein flüchtiges Wattestäbchen, aber seine Minute war vorbei. Du erhältst keine Punkte.",
        "hisopos.type.diamond": "Diamant-Wattestäbchen",
        "hisopos.type.fleeting": "flüchtiges Wattestäbchen",
        "hisopos.type.mystery": "mysteriöses Wattestäbchen",
        "hisopos.type.putrid": "verrottetes Wattestäbchen",
        "hisopos.type.radioactive": "radioaktives Wattestäbchen",
        "hisopos.type.fake": "falsches Wattestäbchen",
        "hisopos.type.twin": "Zwillings-Wattestäbchen",
    },
    "eu": {
        "hisopos.appeared_mystery": "Kotoi-zotz berri bat agertu da!\n{type_label} · balio ezkutua",
        "hisopos.captured_caption_negative": "{user}(e)k {type_label} bat harrapatu eta {points} puntu galdu ditu.",
        "hisopos.captured_popup_negative": "Kotoi-zotza harrapatuta! {points} puntu galdu dituzu.",
        "hisopos.captured_caption_fake": "{user}(e)k kotoi-zotz bat harrapatzear zuen, baina faltsua zen! Ez du punturik ematen.",
        "hisopos.captured_caption_zero": "{user}(e)k {type_label} bat harrapatu du, baina ez du punturik lortu.",
        "hisopos.captured_popup_zero": "Kotoi-zotz honek ez zuen punturik balio.",
        "hisopos.expired_fleeting_caption": "{user}(e)k {type_label} bat aurkitu du, baina haren minutu iheskorra jada igaroa zen. Ez du punturik lortu.",
        "hisopos.expired_fleeting_popup": "Kotoi-zotz iheskor bat zegoen, baina haren minutua igaro da. Ez duzu punturik lortu.",
        "hisopos.type.diamond": "diamantezko kotoi-zotza",
        "hisopos.type.fleeting": "kotoi-zotz iheskorra",
        "hisopos.type.mystery": "kotoi-zotz misteriotsua",
        "hisopos.type.putrid": "kotoi-zotz ustela",
        "hisopos.type.radioactive": "kotoi-zotz erradioaktiboa",
        "hisopos.type.fake": "kotoi-zotz faltsua",
        "hisopos.type.twin": "kotoi-zotz bikia",
    },
    "fr": {
        "hisopos.appeared_mystery": "Un nouveau coton-tige est apparu !\n{type_label} · valeur cachée",
        "hisopos.captured_caption_negative": "{user} a capturé un {type_label} et perdu {points} pt.",
        "hisopos.captured_popup_negative": "Coton-tige capturé ! Tu as perdu {points} pt.",
        "hisopos.captured_caption_fake": "{user} allait capturer un coton-tige, mais il s'est avéré faux ! Il ne rapporte aucun point.",
        "hisopos.captured_caption_zero": "{user} a capturé un {type_label}, mais n'a gagné aucun point.",
        "hisopos.captured_popup_zero": "Ce coton-tige ne valait aucun point.",
        "hisopos.expired_fleeting_caption": "{user} a trouvé un {type_label}, mais sa minute fugace était déjà passée. Aucun point gagné.",
        "hisopos.expired_fleeting_popup": "Il y avait un coton-tige fugace, mais sa minute était passée. Tu ne gagnes aucun point.",
        "hisopos.type.diamond": "coton-tige diamant",
        "hisopos.type.fleeting": "coton-tige fugace",
        "hisopos.type.mystery": "coton-tige mystérieux",
        "hisopos.type.putrid": "coton-tige putride",
        "hisopos.type.radioactive": "coton-tige radioactif",
        "hisopos.type.fake": "faux coton-tige",
        "hisopos.type.twin": "coton-tige jumeau",
    },
    "gn": {
        "hisopos.appeared_mystery": "Ojekuaa peteĩ hisopo pyahu!\n{type_label} · hepykue ñemi",
        "hisopos.captured_caption_negative": "{user} ojapyhy peteĩ {type_label} ha operde {points} kyta.",
        "hisopos.captured_popup_negative": "Hisopo ojejapyhy! Reperde {points} kyta.",
        "hisopos.captured_caption_fake": "{user} ojapyhýta kuri peteĩ hisopo, péro ha'e gua'u! Nome'ẽi mba'eveichagua kyta.",
        "hisopos.captured_caption_zero": "{user} ojapyhy peteĩ {type_label}, hákatu ndohupytýi kyta.",
        "hisopos.captured_popup_zero": "Ko hisopo ndovaléi kyta.",
        "hisopos.expired_fleeting_caption": "{user} ojuhu peteĩ {type_label}, hákatu iminúto pya'e ohasáma. Nohupytýi kyta.",
        "hisopos.expired_fleeting_popup": "Oĩkuri peteĩ hisopo pya'e, hákatu iminúto ohasáma. Nderehupytýi kyta.",
        "hisopos.type.diamond": "hisopo diamante",
        "hisopos.type.fleeting": "hisopo pya'e",
        "hisopos.type.mystery": "hisopo ñemigua",
        "hisopos.type.putrid": "hisopo tujúva",
        "hisopos.type.radioactive": "hisopo radiactivo",
        "hisopos.type.fake": "hisopo gua'u",
        "hisopos.type.twin": "hisopo kõi",
    },
    "it": {
        "hisopos.appeared_mystery": "È apparso un nuovo cotton fioc!\n{type_label} · valore nascosto",
        "hisopos.captured_caption_negative": "{user} ha catturato un {type_label} e ha perso {points} pt.",
        "hisopos.captured_popup_negative": "Cotton fioc catturato! Hai perso {points} pt.",
        "hisopos.captured_caption_fake": "{user} stava per catturare un cotton fioc, ma si è rivelato falso! Non vale alcun punto.",
        "hisopos.captured_caption_zero": "{user} ha catturato un {type_label}, ma non ha ottenuto punti.",
        "hisopos.captured_popup_zero": "Questo cotton fioc non valeva punti.",
        "hisopos.expired_fleeting_caption": "{user} ha trovato un {type_label}, ma il suo minuto fugace era già passato. Nessun punto ottenuto.",
        "hisopos.expired_fleeting_popup": "C'era un cotton fioc fugace, ma il suo minuto era passato. Non hai ottenuto punti.",
        "hisopos.type.diamond": "cotton fioc diamante",
        "hisopos.type.fleeting": "cotton fioc fugace",
        "hisopos.type.mystery": "cotton fioc misterioso",
        "hisopos.type.putrid": "cotton fioc putrefatto",
        "hisopos.type.radioactive": "cotton fioc radioattivo",
        "hisopos.type.fake": "cotton fioc falso",
        "hisopos.type.twin": "cotton fioc gemello",
    },
    "ja": {
        "hisopos.appeared_mystery": "新しい綿棒が現れた！\n{type_label}・価値は秘密",
        "hisopos.captured_caption_negative": "{user}が{type_label}を捕まえ、{points}ポイント失った。",
        "hisopos.captured_popup_negative": "綿棒を捕獲！{points}ポイント失いました。",
        "hisopos.captured_caption_fake": "{user}は綿棒を捕まえようとしたが、偽物だった！ポイントは加算されない。",
        "hisopos.captured_caption_zero": "{user}が{type_label}を捕まえたが、ポイントは増えなかった。",
        "hisopos.captured_popup_zero": "この綿棒にはポイントがありませんでした。",
        "hisopos.expired_fleeting_caption": "{user}が{type_label}を見つけたが、1分の制限時間はすでに過ぎていた。ポイントは獲得できなかった。",
        "hisopos.expired_fleeting_popup": "一瞬の綿棒だったが、1分はもう過ぎていました。ポイントは獲得できません。",
        "hisopos.type.diamond": "ダイヤモンド綿棒",
        "hisopos.type.fleeting": "一瞬の綿棒",
        "hisopos.type.mystery": "ミステリー綿棒",
        "hisopos.type.putrid": "腐敗した綿棒",
        "hisopos.type.radioactive": "放射性綿棒",
        "hisopos.type.fake": "偽物の綿棒",
        "hisopos.type.twin": "双子の綿棒",
    },
    "la": {
        "hisopos.appeared_mystery": "Novum bacillum gossypinum apparuit!\n{type_label} · pretium occultum",
        "hisopos.captured_caption_negative": "{user} {type_label} cepit et {points} puncta amisit.",
        "hisopos.captured_popup_negative": "Bacillum captum! {points} puncta amisisti.",
        "hisopos.captured_caption_fake": "{user} bacillum capere volebat, sed falsum apparuit! Nulla puncta tribuit.",
        "hisopos.captured_caption_zero": "{user} {type_label} cepit, sed nulla puncta accepit.",
        "hisopos.captured_popup_zero": "Hoc bacillum nulla puncta valebat.",
        "hisopos.expired_fleeting_caption": "{user} {type_label} invenit, sed momentum fugax iam praeterierat. Nulla puncta accepit.",
        "hisopos.expired_fleeting_popup": "Bacillum fugax inerat, sed momentum eius praeteriit. Nulla puncta accepisti.",
        "hisopos.type.diamond": "bacillum adamantinum",
        "hisopos.type.fleeting": "bacillum fugax",
        "hisopos.type.mystery": "bacillum arcanum",
        "hisopos.type.putrid": "bacillum putridum",
        "hisopos.type.radioactive": "bacillum radioactivum",
        "hisopos.type.fake": "bacillum falsum",
        "hisopos.type.twin": "bacillum geminum",
    },
    "nl": {
        "hisopos.appeared_mystery": "Er is een nieuw wattenstaafje verschenen!\n{type_label} · verborgen waarde",
        "hisopos.captured_caption_negative": "{user} ving een {type_label} en verloor {points} pt.",
        "hisopos.captured_popup_negative": "Wattenstaafje gevangen! Je verloor {points} pt.",
        "hisopos.captured_caption_fake": "{user} wilde een wattenstaafje vangen, maar het bleek nep! Het levert geen punten op.",
        "hisopos.captured_caption_zero": "{user} ving een {type_label}, maar kreeg geen punten.",
        "hisopos.captured_popup_zero": "Dit wattenstaafje was geen punten waard.",
        "hisopos.expired_fleeting_caption": "{user} vond een {type_label}, maar de vluchtige minuut was al voorbij. Geen punten verdiend.",
        "hisopos.expired_fleeting_popup": "Er zat een vluchtig wattenstaafje in, maar de minuut was voorbij. Je krijgt geen punten.",
        "hisopos.type.diamond": "diamanten wattenstaafje",
        "hisopos.type.fleeting": "vluchtig wattenstaafje",
        "hisopos.type.mystery": "mysterieus wattenstaafje",
        "hisopos.type.putrid": "verrot wattenstaafje",
        "hisopos.type.radioactive": "radioactief wattenstaafje",
        "hisopos.type.fake": "nep-wattenstaafje",
        "hisopos.type.twin": "tweeling-wattenstaafje",
    },
    "pt_BR": {
        "hisopos.appeared_mystery": "Um novo cotonete apareceu!\n{type_label} · valor oculto",
        "hisopos.captured_caption_negative": "{user} capturou um {type_label} e perdeu {points} pt.",
        "hisopos.captured_popup_negative": "Cotonete capturado! Você perdeu {points} pt.",
        "hisopos.captured_caption_fake": "{user} ia capturar um cotonete, mas ele era falso! Não vale nenhum ponto.",
        "hisopos.captured_caption_zero": "{user} capturou um {type_label}, mas não ganhou pontos.",
        "hisopos.captured_popup_zero": "Este cotonete não valia pontos.",
        "hisopos.expired_fleeting_caption": "{user} encontrou um {type_label}, mas o minuto fugaz já tinha passado. Não ganhou pontos.",
        "hisopos.expired_fleeting_popup": "Havia um cotonete fugaz, mas o minuto dele passou. Você não ganhou pontos.",
        "hisopos.type.diamond": "cotonete diamante",
        "hisopos.type.fleeting": "cotonete fugaz",
        "hisopos.type.mystery": "cotonete misterioso",
        "hisopos.type.putrid": "cotonete pútrido",
        "hisopos.type.radioactive": "cotonete radioativo",
        "hisopos.type.fake": "cotonete falso",
        "hisopos.type.twin": "cotonete gêmeo",
    },
    "pt_PT": {
        "hisopos.appeared_mystery": "Apareceu um novo cotonete!\n{type_label} · valor oculto",
        "hisopos.captured_caption_negative": "{user} capturou um {type_label} e perdeu {points} pt.",
        "hisopos.captured_popup_negative": "Cotonete capturado! Perdeste {points} pt.",
        "hisopos.captured_caption_fake": "{user} ia capturar um cotonete, mas revelou-se falso! Não vale qualquer ponto.",
        "hisopos.captured_caption_zero": "{user} capturou um {type_label}, mas não ganhou pontos.",
        "hisopos.captured_popup_zero": "Este cotonete não valia pontos.",
        "hisopos.expired_fleeting_caption": "{user} encontrou um {type_label}, mas o minuto fugaz já tinha passado. Não ganhou pontos.",
        "hisopos.expired_fleeting_popup": "Havia um cotonete fugaz, mas o minuto dele passou. Não ganhaste pontos.",
        "hisopos.type.diamond": "cotonete diamante",
        "hisopos.type.fleeting": "cotonete fugaz",
        "hisopos.type.mystery": "cotonete misterioso",
        "hisopos.type.putrid": "cotonete pútrido",
        "hisopos.type.radioactive": "cotonete radioativo",
        "hisopos.type.fake": "cotonete falso",
        "hisopos.type.twin": "cotonete gémeo",
    },
    "quz": {
        "hisopos.appeared_mystery": "Musuq hisopo rikurimun!\n{type_label} · pakasqa chanin",
        "hisopos.captured_caption_negative": "{user} huk {type_label} hap'ispa {points} puntuta chinkachin.",
        "hisopos.captured_popup_negative": "Hisopo hap'isqa! {points} puntuta chinkachinki.",
        "hisopos.captured_caption_fake": "{user} huk hisopota hap'iyta munarqan, ichaqa llulla kasqa! Mana ima puntutapas yapanchu.",
        "hisopos.captured_caption_zero": "{user} huk {type_label} hap'irqan, ichaqa mana puntuta yaparqanchu.",
        "hisopos.captured_popup_zero": "Kay hisopoqa mana puntuyuqchu karqan.",
        "hisopos.expired_fleeting_caption": "{user} huk {type_label} tarirqan, ichaqa utqay minutunña pasarqan. Mana puntuta yaparqanchu.",
        "hisopos.expired_fleeting_popup": "Utqay hisopo karqan, ichaqa minutunña pasarqan. Mana puntuta yapankichu.",
        "hisopos.type.diamond": "diamante hisopo",
        "hisopos.type.fleeting": "utqay hisopo",
        "hisopos.type.mystery": "pakasqa hisopo",
        "hisopos.type.putrid": "ismuq hisopo",
        "hisopos.type.radioactive": "radiactivo hisopo",
        "hisopos.type.fake": "llulla hisopo",
        "hisopos.type.twin": "iskay hisopo",
    },
    "ru": {
        "hisopos.appeared_mystery": "Появилась новая ватная палочка!\n{type_label} · скрытая ценность",
        "hisopos.captured_caption_negative": "{user} поймал {type_label} и потерял {points} очк.",
        "hisopos.captured_popup_negative": "Палочка поймана! Вы потеряли {points} очк.",
        "hisopos.captured_caption_fake": "{user} собирался поймать ватную палочку, но она оказалась поддельной! Очки не начисляются.",
        "hisopos.captured_caption_zero": "{user} поймал {type_label}, но не получил очков.",
        "hisopos.captured_popup_zero": "Эта палочка не стоила очков.",
        "hisopos.expired_fleeting_caption": "{user} нашёл {type_label}, но его короткая минута уже прошла. Очки не начислены.",
        "hisopos.expired_fleeting_popup": "Внутри была мимолётная ватная палочка, но её минута прошла. Вы не получили очков.",
        "hisopos.type.diamond": "алмазная ватная палочка",
        "hisopos.type.fleeting": "мимолётная ватная палочка",
        "hisopos.type.mystery": "таинственная ватная палочка",
        "hisopos.type.putrid": "гнилая ватная палочка",
        "hisopos.type.radioactive": "радиоактивная ватная палочка",
        "hisopos.type.fake": "поддельная ватная палочка",
        "hisopos.type.twin": "ватная палочка-близнец",
    },
    "zh_Hans": {
        "hisopos.appeared_mystery": "出现了一根新棉签！\n{type_label} · 隐藏分值",
        "hisopos.captured_caption_negative": "{user}捕获了{type_label}，失去{points}分。",
        "hisopos.captured_popup_negative": "棉签已捕获！你失去了{points}分。",
        "hisopos.captured_caption_fake": "{user}正要捕获一根棉签，结果发现是假的！不会获得任何分数。",
        "hisopos.captured_caption_zero": "{user}捕获了{type_label}，但没有获得分数。",
        "hisopos.captured_popup_zero": "这根棉签不值分数。",
        "hisopos.expired_fleeting_caption": "{user}发现了{type_label}，但它的一分钟时限已经过去，没有获得分数。",
        "hisopos.expired_fleeting_popup": "里面是瞬逝棉签，但它的一分钟已经过去。你没有获得分数。",
        "hisopos.type.diamond": "钻石棉签",
        "hisopos.type.fleeting": "瞬逝棉签",
        "hisopos.type.mystery": "神秘棉签",
        "hisopos.type.putrid": "腐烂棉签",
        "hisopos.type.radioactive": "放射性棉签",
        "hisopos.type.fake": "假棉签",
        "hisopos.type.twin": "双生棉签",
    },
    "zh_Hant": {
        "hisopos.appeared_mystery": "出現了一根新棉花棒！\n{type_label} · 隱藏分值",
        "hisopos.captured_caption_negative": "{user}捕獲了{type_label}，失去{points}分。",
        "hisopos.captured_popup_negative": "棉花棒已捕獲！你失去了{points}分。",
        "hisopos.captured_caption_fake": "{user}正要捕獲一根棉花棒，結果發現是假的！不會獲得任何分數。",
        "hisopos.captured_caption_zero": "{user}捕獲了{type_label}，但沒有獲得分數。",
        "hisopos.captured_popup_zero": "這根棉花棒不值分數。",
        "hisopos.expired_fleeting_caption": "{user}發現了{type_label}，但它的一分鐘時限已經過去，沒有獲得分數。",
        "hisopos.expired_fleeting_popup": "裡面是瞬逝棉花棒，但它的一分鐘已經過去。你沒有獲得分數。",
        "hisopos.type.diamond": "鑽石棉花棒",
        "hisopos.type.fleeting": "瞬逝棉花棒",
        "hisopos.type.mystery": "神秘棉花棒",
        "hisopos.type.putrid": "腐爛棉花棒",
        "hisopos.type.radioactive": "放射性棉花棒",
        "hisopos.type.fake": "假棉花棒",
        "hisopos.type.twin": "雙生棉花棒",
    },
}

HISOPO_RULE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "help.reglashisopo": "muestra las reglas del Recolector de Hisopos",
        "hisopos.rules": (
            "Reglas del Recolector de Hisopos\n\n"
            "- Funciona en grupos y supergrupos. Viene habilitado y un admin puede ajustar en /config una intensidad de 1, 5, 10, 15 o 20 % por mensaje válido.\n"
            "- Cuando aparece un Hisopo, la primera persona que toca «Capturar hisopo» se lo queda. Los clics posteriores no suman.\n"
            "- Común: 47 %, +1 pt.\n"
            "- Plateado: 14 %, +2 pt.\n"
            "- Dorado: 10 %, +3 pt.\n"
            "- Fugaz: 7 %, +5 pt y vence al minuto.\n"
            "- Misterioso: 7 %, oculta uno de los otros tipos durante 20 minutos. Si contiene un Fugaz, sus +5 pt vencen al minuto; después revela el Fugaz por 0 pt.\n"
            "- Putrefacto: 5 %, se disfraza de común, plateado, dorado o diamante y resta 2 pt al capturarlo.\n"
            "- Radiactivo: 4 %, vale -3 pt en los minutos 0-4, -1 en 5-9, +2 en 10-14, +4 en 15-17 y +6 en 18-19.\n"
            "- Falso: 3 %, aparece disfrazado, vale 0 y no programa otra aparición.\n"
            "- Gemelo: 2 %, +4 pt, lanza otro Hisopo en el momento y programa uno para el día siguiente.\n"
            "- Diamante: 1 %, +10 pt.\n"
            "- Si nadie captura un Hisopo, se vence y no le quita puntos a nadie. Los normales vencen a los 20 minutos y el Fugaz directo al minuto. Los puntajes pueden quedar negativos.\n"
            "- Cada captura válida programa una aparición para el día siguiente, salvo el Falso y el Fugaz oculto cuyo minuto venció.\n"
            "- /hisopos muestra la tabla del grupo."
        ),
    },
    "en": {
        "help.reglashisopo": "shows the Swab Collector rules",
        "hisopos.rules": (
            "Swab Collector rules\n\n"
            "- It works in groups and supergroups. It starts enabled, and an admin can set a 1, 5, 10, 15, or 20% chance per valid message in /config.\n"
            "- When a Swab appears, the first person to press ‘Capture swab’ gets it. Later taps score nothing.\n"
            "- Common: 47%, +1 pt.\n"
            "- Silver: 14%, +2 pt.\n"
            "- Gold: 10%, +3 pt.\n"
            "- Fleeting: 7%, +5 pt and expires after one minute.\n"
            "- Mystery: 7%, hides one of the other types for 20 minutes. If it contains a Fleeting Swab, its +5 pt expire after one minute; it is then revealed for 0 pt.\n"
            "- Putrid: 5%, disguises itself as common, silver, gold, or diamond and subtracts 2 pt when captured.\n"
            "- Radioactive: 4%, worth -3 pt at minutes 0-4, -1 at 5-9, +2 at 10-14, +4 at 15-17, and +6 at 18-19.\n"
            "- Fake: 3%, appears disguised, is worth 0, and schedules no extra appearance.\n"
            "- Twin: 2%, +4 pt, spawns another Swab immediately and schedules one for the next day.\n"
            "- Diamond: 1%, +10 pt.\n"
            "- If nobody captures a Swab, it expires without taking points from anyone. Regular ones expire after 20 minutes and a direct Fleeting one after a minute. Scores may be negative.\n"
            "- Every valid capture schedules an appearance for the next day, except a Fake and a hidden Fleeting whose minute expired.\n"
            "- /hisopos shows the group leaderboard."
        ),
    },
    "es_ES": {
        "help.reglashisopo": "muestra las reglas del Recolector de Hisopos",
        "hisopos.rules": (
            "Reglas del Recolector de Hisopos\n\n"
            "- Funciona en grupos y supergrupos. Viene activado y un administrador puede ajustar en /config una intensidad del 1, 5, 10, 15 o 20 % por mensaje válido.\n"
            "- Cuando aparece un hisopo, se lo queda la primera persona que pulsa «Capturar hisopo». Las pulsaciones posteriores no suman.\n"
            "- Común: 47 %, +1 pt.\n- Plateado: 14 %, +2 pt.\n- Dorado: 10 %, +3 pt.\n"
            "- Fugaz: 7 %, +5 pt y caduca al minuto.\n"
            "- Misterioso: 7 %, oculta uno de los demás tipos durante 20 minutos. Si contiene un Fugaz, sus +5 pt caducan al minuto; después lo revela por 0 pt.\n"
            "- Putrefacto: 5 %, se disfraza de común, plateado, dorado o diamante y resta 2 pt al capturarlo.\n"
            "- Radiactivo: 4 %, vale -3 pt en los minutos 0-4, -1 en 5-9, +2 en 10-14, +4 en 15-17 y +6 en 18-19.\n"
            "- Falso: 3 %, aparece disfrazado, vale 0 y no programa otra aparición.\n"
            "- Gemelo: 2 %, +4 pt, hace aparecer otro hisopo al instante y programa uno para el día siguiente.\n"
            "- Diamante: 1 %, +10 pt.\n"
            "- Si nadie captura un hisopo, caduca sin quitar puntos a nadie. Los normales caducan a los 20 minutos y el Fugaz directo al minuto. La puntuación puede ser negativa.\n"
            "- Cada captura válida programa una aparición para el día siguiente, salvo el Falso y el Fugaz oculto cuyo minuto caducó.\n"
            "- /hisopos muestra la tabla del grupo."
        ),
    },
    "ca": {
        "help.reglashisopo": "mostra les regles del Recol·lector de Bastonets",
        "hisopos.rules": (
            "Regles del Recol·lector de Bastonets\n\n"
            "- Funciona en grups i supergrups. Ve activat i un administrador pot ajustar a /config una probabilitat de l'1, 5, 10, 15 o 20 % per missatge vàlid.\n"
            "- Quan apareix un bastonet, la primera persona que prem «Captura el bastonet» se'l queda. Els tocs posteriors no puntuen.\n"
            "- Comú: 47 %, +1 pt.\n- Platejat: 14 %, +2 pt.\n- Daurat: 10 %, +3 pt.\n"
            "- Fugaç: 7 %, +5 pt i caduca al cap d'un minut.\n"
            "- Misteriós: 7 %, amaga un dels altres tipus durant 20 minuts. Si conté un Fugaç, els +5 pt caduquen al minut; després es revela per 0 pt.\n"
            "- Putrefacte: 5 %, es disfressa de comú, platejat, daurat o diamant i resta 2 pt quan es captura.\n"
            "- Radioactiu: 4 %, val -3 pt als minuts 0-4, -1 als 5-9, +2 als 10-14, +4 als 15-17 i +6 als 18-19.\n"
            "- Fals: 3 %, apareix disfressat, val 0 i no programa cap altra aparició.\n"
            "- Bessó: 2 %, +4 pt, fa aparèixer un altre bastonet al moment i en programa un per a l'endemà.\n"
            "- Diamant: 1 %, +10 pt.\n"
            "- Si ningú captura un bastonet, caduca sense restar punts a ningú. Els normals caduquen als 20 minuts i el Fugaç directe al minut. La puntuació pot ser negativa.\n"
            "- Cada captura vàlida programa una aparició per a l'endemà, tret del Fals i del Fugaç ocult amb el minut vençut.\n"
            "- /hisopos mostra la classificació del grup."
        ),
    },
    "de": {
        "help.reglashisopo": "zeigt die Regeln des Wattestäbchen-Sammlers",
        "hisopos.rules": (
            "Regeln des Wattestäbchen-Sammlers\n\n"
            "- Das Spiel läuft in Gruppen und Supergruppen und ist standardmäßig aktiv. Ein Admin stellt in /config eine Chance von 1, 5, 10, 15 oder 20 % pro gültiger Nachricht ein.\n"
            "- Wer zuerst auf „Wattestäbchen fangen“ tippt, erhält es. Spätere Klicks geben keine Punkte.\n"
            "- Gewöhnlich: 47 %, +1 Pkt.\n- Silber: 14 %, +2 Pkt.\n- Gold: 10 %, +3 Pkt.\n"
            "- Flüchtig: 7 %, +5 Pkt. und verfällt nach einer Minute.\n"
            "- Mysteriös: 7 %, verbirgt 20 Minuten lang einen anderen Typ. Enthält es ein Flüchtiges, verfallen dessen +5 Pkt. nach einer Minute; danach wird es für 0 Pkt. enthüllt.\n"
            "- Verrottet: 5 %, tarnt sich als gewöhnlich, silbern, golden oder diamant und zieht beim Fangen 2 Pkt. ab.\n"
            "- Radioaktiv: 4 %, gibt -3 Pkt. in Minute 0-4, -1 in 5-9, +2 in 10-14, +4 in 15-17 und +6 in 18-19.\n"
            "- Falsch: 3 %, erscheint getarnt, ist 0 wert und plant kein weiteres Erscheinen.\n"
            "- Zwilling: 2 %, +4 Pkt., erzeugt sofort ein weiteres und plant eines für den nächsten Tag.\n"
            "- Diamant: 1 %, +10 Pkt.\n"
            "- Wird keines gefangen, verfällt es ohne Punktabzug. Normale verfallen nach 20 Minuten, direkte Flüchtige nach einer Minute. Punktestände dürfen negativ sein.\n"
            "- Jeder gültige Fang plant eines für den nächsten Tag, außer Falsch und einem versteckten Flüchtigen nach Ablauf seiner Minute.\n"
            "- /hisopos zeigt die Gruppenrangliste."
        ),
    },
    "eu": {
        "help.reglashisopo": "Kotoi Biltzailearen arauak erakusten ditu",
        "hisopos.rules": (
            "Kotoi Biltzailearen arauak\n\n"
            "- Talde eta supertaldeetan dabil eta lehenetsita aktibo dago. Administratzaileak /config bidez % 1, 5, 10, 15 edo 20ko aukera ezar dezake baliozko mezu bakoitzeko.\n"
            "- «Harrapatu kotoi-zotza» lehenengo sakatzen duenak irabazten du; ondorengoek ez dute punturik.\n"
            "- Arrunta: % 47, +1 puntu.\n- Zilarrezkoa: % 14, +2.\n- Urrezkoa: % 10, +3.\n"
            "- Iheskorra: % 7, +5 eta minutu batean iraungitzen da.\n"
            "- Misteriotsua: % 7, beste mota bat ezkutatzen du 20 minutuz. Iheskorra bada, +5 puntuak minutu batean iraungitzen dira; gero 0 punturekin agertzen da.\n"
            "- Ustela: % 5, arrunt, zilar, urre edo diamante gisa mozorrotzen da eta harrapatzean 2 puntu kentzen ditu.\n"
            "- Erradioaktiboa: % 4, -3 puntu 0-4 minutuetan, -1 5-9an, +2 10-14an, +4 15-17an eta +6 18-19an.\n"
            "- Faltsua: % 3, mozorrotuta agertzen da, 0 balio du eta ez du beste agerpenik programatzen.\n"
            "- Bikia: % 2, +4, berehala beste bat sortzen du eta biharamunerako bat programatzen du.\n"
            "- Diamantea: % 1, +10.\n"
            "- Inork harrapatzen ez badu, iraungitzen da inori punturik kendu gabe. Arruntak 20 minutuan eta Iheskor zuzena minutu batean iraungitzen dira. Puntuazioa negatiboa izan daiteke.\n"
            "- Baliozko harrapaketa bakoitzak biharamunerako agerpen bat programatzen du, Faltsuak eta iraungitako Iheskor ezkutuak izan ezik.\n"
            "- /hisopos taldeko sailkapena da."
        ),
    },
    "fr": {
        "help.reglashisopo": "affiche les règles du Collectionneur de Cotons-tiges",
        "hisopos.rules": (
            "Règles du Collectionneur de Cotons-tiges\n\n"
            "- Il fonctionne dans les groupes et supergroupes et est activé par défaut. Un admin règle dans /config une chance de 1, 5, 10, 15 ou 20 % par message valide.\n"
            "- La première personne qui appuie sur « Capturer le coton-tige » le gagne. Les suivantes ne marquent rien.\n"
            "- Commun : 47 %, +1 pt.\n- Argent : 14 %, +2 pt.\n- Or : 10 %, +3 pt.\n"
            "- Fugace : 7 %, +5 pt et expire après une minute.\n"
            "- Mystérieux : 7 %, cache un autre type pendant 20 minutes. S'il contient un Fugace, ses +5 pt expirent après une minute ; il est ensuite révélé pour 0 pt.\n"
            "- Putride : 5 %, se déguise en commun, argent, or ou diamant et retire 2 pt à la capture.\n"
            "- Radioactif : 4 %, vaut -3 pt aux minutes 0-4, -1 aux 5-9, +2 aux 10-14, +4 aux 15-17 et +6 aux 18-19.\n"
            "- Faux : 3 %, apparaît déguisé, vaut 0 et ne programme aucune autre apparition.\n"
            "- Jumeau : 2 %, +4 pt, fait apparaître immédiatement un autre coton-tige et en programme un pour le lendemain.\n"
            "- Diamant : 1 %, +10 pt.\n"
            "- Si personne ne le capture, il expire sans retirer de points. Les normaux expirent après 20 minutes et le Fugace direct après une minute. Les scores peuvent être négatifs.\n"
            "- Chaque capture valide programme une apparition le lendemain, sauf le Faux et le Fugace caché dont la minute a expiré.\n"
            "- /hisopos affiche le classement du groupe."
        ),
    },
    "gn": {
        "help.reglashisopo": "ohechauka Hisopo Ñembyatýha mbojojaha",
        "hisopos.rules": (
            "Hisopo Ñembyatýha mbojojaha\n\n"
            "- Omba'apo aty ha supergrupo-pe ha oñemyendy ijeheguiete. Admin omoĩkuaa /config-pe 1, 5, 10, 15 térã 20 % opa ñe'ẽmondo oikóvare.\n"
            "- Pe ojopy raẽva «Ejapyhy hisopo» ogueraha; umi ojopy upe rire ndohupytýi kyta.\n"
            "- Jepivegua: 47 %, +1 kyta.\n- Plata: 14 %, +2.\n- Oro: 10 %, +3.\n"
            "- Pya'e: 7 %, +5 ha oñembyai peteĩ minúto rire.\n"
            "- Ñemigua: 7 %, oñomi ambueichagua 20 minúto aja. Pya'e ramo, +5 opa peteĩ minúto rire; upéi ojekuaa 0 kytáre.\n"
            "- Tujúva: 5 %, oñemonde jepivegua, plata, oro térã diamánteramo ha ojehape'ã 2 kyta ojejapyhývo.\n"
            "- Radiactivo: 4 %, -3 kyta minúto 0-4, -1 5-9, +2 10-14, +4 15-17 ha +6 18-19.\n"
            "- Gua'u: 3 %, ojekuaa ñemiháme, 0 kyta ha nomoĩri ambue jehechauka.\n"
            "- Kõi: 2 %, +4, omoheñói ambue hisopo upepete ha omoĩ peteĩ ko'ẽrõ g̃uarã.\n"
            "- Diamante: 1 %, +10.\n"
            "- Avave ndojapyhýiramo, opa hi'ára oipe'a'ỹre kyta avavégui. Jepivegua opa 20 minútope ha Pya'e tee peteĩ minútope. Ikatu oĩ kyta vai.\n"
            "- Ojejapyhy porãvo oñemoĩ peteĩ jehechauka ko'ẽrõ g̃uarã, Gua'u ha Pya'e ñemi iminúto opámava'ỹre.\n"
            "- /hisopos ohechauka aty rechaukaha."
        ),
    },
    "it": {
        "help.reglashisopo": "mostra le regole del Raccoglitore di Cotton Fioc",
        "hisopos.rules": (
            "Regole del Raccoglitore di Cotton Fioc\n\n"
            "- Funziona in gruppi e supergruppi ed è attivo per impostazione predefinita. Un admin imposta in /config una probabilità dell'1, 5, 10, 15 o 20 % per messaggio valido.\n"
            "- La prima persona che preme «Cattura cotton fioc» lo ottiene; i tocchi successivi non danno punti.\n"
            "- Comune: 47 %, +1 pt.\n- Argento: 14 %, +2 pt.\n- Oro: 10 %, +3 pt.\n"
            "- Fugace: 7 %, +5 pt e scade dopo un minuto.\n"
            "- Misterioso: 7 %, nasconde un altro tipo per 20 minuti. Se contiene un Fugace, i suoi +5 pt scadono dopo un minuto; poi viene rivelato per 0 pt.\n"
            "- Putrefatto: 5 %, si traveste da comune, argento, oro o diamante e sottrae 2 pt alla cattura.\n"
            "- Radioattivo: 4 %, vale -3 pt ai minuti 0-4, -1 ai 5-9, +2 ai 10-14, +4 ai 15-17 e +6 ai 18-19.\n"
            "- Falso: 3 %, appare travestito, vale 0 e non programma altre apparizioni.\n"
            "- Gemello: 2 %, +4 pt, genera subito un altro cotton fioc e ne programma uno per il giorno seguente.\n"
            "- Diamante: 1 %, +10 pt.\n"
            "- Se nessuno lo cattura, scade senza sottrarre punti. I normali scadono dopo 20 minuti e il Fugace diretto dopo un minuto. I punteggi possono essere negativi.\n"
            "- Ogni cattura valida programma un'apparizione per il giorno seguente, salvo il Falso e il Fugace nascosto il cui minuto è scaduto.\n"
            "- /hisopos mostra la classifica del gruppo."
        ),
    },
    "ja": {
        "help.reglashisopo": "綿棒コレクターのルールを表示します",
        "hisopos.rules": (
            "綿棒コレクターのルール\n\n"
            "- グループとスーパーグループで動作し、初期状態で有効です。管理者は /config で有効なメッセージごとの出現率を1、5、10、15、20%に設定できます。\n"
            "- 「綿棒を捕獲」を最初に押した人が獲得し、それ以降のタップには得点がありません。\n"
            "- 通常：47%、+1点。\n- 銀：14%、+2点。\n- 金：10%、+3点。\n"
            "- 一瞬：7%、+5点、1分で期限切れ。\n"
            "- ミステリー：7%、他の種類を20分間隠します。一瞬の綿棒なら+5点は1分で失効し、その後は0点として正体が分かります。\n"
            "- 腐敗：5%、通常・銀・金・ダイヤに変装し、捕獲すると2点減ります。\n"
            "- 放射性：4%、0-4分は-3点、5-9分は-1点、10-14分は+2点、15-17分は+4点、18-19分は+6点。\n"
            "- 偽物：3%、変装して現れ、0点で、次の出現を予約しません。\n"
            "- 双子：2%、+4点、直ちにもう1本出現させ、翌日分も1本予約します。\n"
            "- ダイヤ：1%、+10点。\n"
            "- 誰も捕獲しなければ誰の点も減らさず期限切れになります。通常は20分、直接出た一瞬は1分で期限切れです。得点は負になることがあります。\n"
            "- 有効な捕獲は翌日の出現を予約しますが、偽物と1分を過ぎた隠れ一瞬は例外です。\n"
            "- /hisopos でグループ順位を表示します。"
        ),
    },
    "la": {
        "help.reglashisopo": "regulas Collectoris Bacillorum ostendit",
        "hisopos.rules": (
            "Regulae Collectoris Bacillorum\n\n"
            "- In gregibus et supergregibus operatur atque initio activum est. Administrator in /config probabilitatem 1, 5, 10, 15 aut 20 % pro nuntio valido statuit.\n"
            "- Qui primus «Bacillum cape» premit id accipit; posteriores nulla puncta capiunt.\n"
            "- Commune: 47 %, +1 punctum.\n- Argenteum: 14 %, +2.\n- Aureum: 10 %, +3.\n"
            "- Fugax: 7 %, +5 et post unum minutum perit.\n"
            "- Arcanum: 7 %, aliud genus per 20 minuta celat. Si Fugax inest, +5 post minutum pereunt; deinde pro 0 punctis revelatur.\n"
            "- Putridum: 5 %, commune, argenteum, aureum aut adamantinum simulat et captum 2 puncta aufert.\n"
            "- Radioactivum: 4 %, -3 puncta minutis 0-4, -1 5-9, +2 10-14, +4 15-17 et +6 18-19.\n"
            "- Falsum: 3 %, simulatum apparet, 0 valet neque alium adventum ordinat.\n"
            "- Geminum: 2 %, +4, statim aliud gignit et unum in posterum diem ordinat.\n"
            "- Adamantinum: 1 %, +10.\n"
            "- Si nemo capit, exspirat nec cuiquam puncta aufert. Communia post 20 minuta, Fugax directum post minutum exspirant. Puncta negativa esse possunt.\n"
            "- Quaeque captura valida adventum in posterum diem ordinat, praeter Falsum et Fugax occultum cuius minutum periit.\n"
            "- /hisopos tabulam gregis ostendit."
        ),
    },
    "nl": {
        "help.reglashisopo": "toont de regels van de Wattenstaafjesverzamelaar",
        "hisopos.rules": (
            "Regels van de Wattenstaafjesverzamelaar\n\n"
            "- Werkt in groepen en supergroepen en staat standaard aan. Een beheerder stelt in /config een kans van 1, 5, 10, 15 of 20% per geldig bericht in.\n"
            "- Wie het eerst op ‘Wattenstaafje vangen’ tikt, krijgt het. Latere tikken leveren niets op.\n"
            "- Gewoon: 47%, +1 pt.\n- Zilver: 14%, +2 pt.\n- Goud: 10%, +3 pt.\n"
            "- Vluchtig: 7%, +5 pt en verloopt na één minuut.\n"
            "- Mysterieus: 7%, verbergt 20 minuten een ander type. Bevat het Vluchtig, dan vervalt +5 pt na één minuut; daarna wordt het voor 0 pt onthuld.\n"
            "- Verrot: 5%, vermomt zich als gewoon, zilver, goud of diamant en trekt bij vangst 2 pt af.\n"
            "- Radioactief: 4%, geeft -3 pt in minuut 0-4, -1 in 5-9, +2 in 10-14, +4 in 15-17 en +6 in 18-19.\n"
            "- Nep: 3%, verschijnt vermomd, is 0 waard en plant geen nieuwe verschijning.\n"
            "- Tweeling: 2%, +4 pt, laat meteen nog één verschijnen en plant er één voor de volgende dag.\n"
            "- Diamant: 1%, +10 pt.\n"
            "- Als niemand het vangt, verloopt het zonder punten af te trekken. Gewone verlopen na 20 minuten en directe Vluchtige na één minuut. Scores mogen negatief zijn.\n"
            "- Elke geldige vangst plant er één voor de volgende dag, behalve Nep en een verborgen Vluchtig waarvan de minuut verstreek.\n"
            "- /hisopos toont het groepsklassement."
        ),
    },
    "pt_BR": {
        "help.reglashisopo": "mostra as regras do Coletor de Cotonetes",
        "hisopos.rules": (
            "Regras do Coletor de Cotonetes\n\n"
            "- Funciona em grupos e supergrupos e vem ativado. Um admin configura em /config uma chance de 1, 5, 10, 15 ou 20% por mensagem válida.\n"
            "- A primeira pessoa que tocar em “Capturar cotonete” fica com ele. Toques posteriores não pontuam.\n"
            "- Comum: 47%, +1 pt.\n- Prateado: 14%, +2 pt.\n- Dourado: 10%, +3 pt.\n"
            "- Fugaz: 7%, +5 pt e expira em um minuto.\n"
            "- Misterioso: 7%, esconde outro tipo por 20 minutos. Se contiver um Fugaz, os +5 pt expiram em um minuto; depois ele é revelado por 0 pt.\n"
            "- Pútrido: 5%, se disfarça de comum, prateado, dourado ou diamante e tira 2 pt quando capturado.\n"
            "- Radioativo: 4%, vale -3 pt nos minutos 0-4, -1 em 5-9, +2 em 10-14, +4 em 15-17 e +6 em 18-19.\n"
            "- Falso: 3%, aparece disfarçado, vale 0 e não agenda outra aparição.\n"
            "- Gêmeo: 2%, +4 pt, faz outro aparecer na hora e agenda um para o dia seguinte.\n"
            "- Diamante: 1%, +10 pt.\n"
            "- Se ninguém capturar, ele expira sem tirar pontos de ninguém. Os normais expiram em 20 minutos e o Fugaz direto em um minuto. A pontuação pode ficar negativa.\n"
            "- Cada captura válida agenda uma aparição para o dia seguinte, exceto o Falso e o Fugaz escondido cujo minuto expirou.\n"
            "- /hisopos mostra o ranking do grupo."
        ),
    },
    "pt_PT": {
        "help.reglashisopo": "mostra as regras do Coletor de Cotonetes",
        "hisopos.rules": (
            "Regras do Coletor de Cotonetes\n\n"
            "- Funciona em grupos e supergrupos e vem ativado. Um administrador configura em /config uma probabilidade de 1, 5, 10, 15 ou 20 % por mensagem válida.\n"
            "- A primeira pessoa que carregar em «Capturar cotonete» fica com ele. Os toques seguintes não pontuam.\n"
            "- Comum: 47 %, +1 pt.\n- Prateado: 14 %, +2 pt.\n- Dourado: 10 %, +3 pt.\n"
            "- Fugaz: 7 %, +5 pt e expira num minuto.\n"
            "- Misterioso: 7 %, esconde outro tipo durante 20 minutos. Se contiver um Fugaz, os +5 pt expiram num minuto; depois é revelado por 0 pt.\n"
            "- Pútrido: 5 %, disfarça-se de comum, prateado, dourado ou diamante e retira 2 pt ao ser capturado.\n"
            "- Radioativo: 4 %, vale -3 pt nos minutos 0-4, -1 nos 5-9, +2 nos 10-14, +4 nos 15-17 e +6 nos 18-19.\n"
            "- Falso: 3 %, aparece disfarçado, vale 0 e não agenda outra aparição.\n"
            "- Gémeo: 2 %, +4 pt, faz aparecer outro no momento e agenda um para o dia seguinte.\n"
            "- Diamante: 1 %, +10 pt.\n"
            "- Se ninguém o capturar, expira sem retirar pontos. Os normais expiram em 20 minutos e o Fugaz direto num minuto. A pontuação pode ser negativa.\n"
            "- Cada captura válida agenda uma aparição para o dia seguinte, exceto o Falso e o Fugaz oculto cujo minuto expirou.\n"
            "- /hisopos mostra a classificação do grupo."
        ),
    },
    "quz": {
        "help.reglashisopo": "Hisopo Huñuqpa kamachinkunanta rikuchin",
        "hisopos.rules": (
            "Hisopo Huñuqpa kamachinkuna\n\n"
            "- Huñunakuykunapi, supergrupokunapipas llamk'an, qallariypitaq hap'ichisqa. Admin /config nisqapi 1, 5, 10, 15 utaq 20 % chaylla churayta atin allin willakuypaq.\n"
            "- «Hisopota hap'iy» ñawpaq ñit'iqmi hap'in; qhipapi ñit'iqkuna mana puntuta chaskinkuchu.\n"
            "- Sapsi: 47 %, +1 puntu.\n- Qullqi: 14 %, +2.\n- Quri: 10 %, +3.\n"
            "- Utqay: 7 %, +5, huk minutupi tukukun.\n"
            "- Pakasqa: 7 %, huk rikch'aqta 20 minututa pakan. Utqay kaptinqa +5 puntun huk minutupi tukukun; chaymanta 0 puntuwan rikuchikun.\n"
            "- Ismuq: 5 %, sapsi, qullqi, quri utaq diamante hina rikuchikun, hap'iptintaq 2 puntuta qichun.\n"
            "- Radiactivo: 4 %, -3 puntu 0-4 minutupi, -1 5-9, +2 10-14, +4 15-17, +6 18-19.\n"
            "- Llulla: 3 %, huk hina rikuchikun, 0 puntu, manataq huk rikuriyta wakichinchu.\n"
            "- Iskay: 2 %, +4, huk hisopota chaylla rikurichin, huktaq paqarinpaq wakichin.\n"
            "- Diamante: 1 %, +10.\n"
            "- Mana pipas hap'iptinqa pachan tukukun, manataq pipas puntuta chinkachinchu. Sapsikuna 20 minutupi, Utqay chiqaptaq huk minutupi tukukun. Yupayqa mana allinmanpas chayayta atin.\n"
            "- Sapa allin hap'iy paqarinpaq huk rikuriyta wakichin, Llullatawan pakasqa Utqaypa minutun tukusqata mana.\n"
            "- /hisopos huñunakuypa yupayninta rikuchin."
        ),
    },
    "ru": {
        "help.reglashisopo": "показывает правила Собирателя ватных палочек",
        "hisopos.rules": (
            "Правила Собирателя ватных палочек\n\n"
            "- Игра работает в группах и супергруппах и включена по умолчанию. Администратор задаёт в /config шанс 1, 5, 10, 15 или 20 % на допустимое сообщение.\n"
            "- Палочку получает тот, кто первым нажал «Поймать палочку». Последующие нажатия очков не дают.\n"
            "- Обычная: 47 %, +1 очко.\n- Серебряная: 14 %, +2.\n- Золотая: 10 %, +3.\n"
            "- Мимолётная: 7 %, +5 и исчезает через минуту.\n"
            "- Таинственная: 7 %, скрывает другой вид 20 минут. Если внутри Мимолётная, её +5 сгорают через минуту; затем она раскрывается за 0 очков.\n"
            "- Гнилая: 5 %, маскируется под обычную, серебряную, золотую или алмазную и отнимает 2 очка при поимке.\n"
            "- Радиоактивная: 4 %, даёт -3 очка на минутах 0-4, -1 на 5-9, +2 на 10-14, +4 на 15-17 и +6 на 18-19.\n"
            "- Поддельная: 3 %, появляется замаскированной, стоит 0 и не планирует новое появление.\n"
            "- Близнец: 2 %, +4, сразу создаёт ещё одну палочку и планирует одну на следующий день.\n"
            "- Алмазная: 1 %, +10.\n"
            "- Если никто не поймал палочку, срок её действия истечёт без штрафа. Обычные живут 20 минут, прямая Мимолётная — минуту. Счёт может быть отрицательным.\n"
            "- Каждая удачная поимка планирует появление на следующий день, кроме Поддельной и скрытой Мимолётной с истёкшей минутой.\n"
            "- /hisopos показывает таблицу группы."
        ),
    },
    "zh_Hans": {
        "help.reglashisopo": "显示棉签收集者规则",
        "hisopos.rules": (
            "棉签收集者规则\n\n"
            "- 游戏用于群组和超级群组，默认开启。管理员可在 /config 中把每条有效消息的出现概率设为1%、5%、10%、15%或20%。\n"
            "- 最先点击“捕获棉签”的人获得棉签；之后的点击不得分。\n"
            "- 普通：47%，+1分。\n- 银：14%，+2分。\n- 金：10%，+3分。\n"
            "- 瞬逝：7%，+5分，一分钟后失效。\n"
            "- 神秘：7%，将其他一种类型隐藏20分钟。若其中是瞬逝棉签，+5分在一分钟后失效；之后以0分揭晓。\n"
            "- 腐烂：5%，伪装成普通、银、金或钻石，捕获时扣2分。\n"
            "- 放射性：4%，第0-4分钟为-3分，5-9分钟-1分，10-14分钟+2分，15-17分钟+4分，18-19分钟+6分。\n"
            "- 假：3%，伪装出现，价值0分，不安排下一次出现。\n"
            "- 双生：2%，+4分，立刻再生成一根，并安排次日一根。\n"
            "- 钻石：1%，+10分。\n"
            "- 若无人捕获，棉签会失效，不扣任何人的分。普通棉签20分钟失效，直接出现的瞬逝棉签一分钟失效。分数可以为负。\n"
            "- 每次有效捕获都会安排次日出现，但假棉签和超过一分钟的隐藏瞬逝棉签除外。\n"
            "- /hisopos 显示本群排行榜。"
        ),
    },
    "zh_Hant": {
        "help.reglashisopo": "顯示棉花棒收集者規則",
        "hisopos.rules": (
            "棉花棒收集者規則\n\n"
            "- 遊戲用於群組和超級群組，預設開啟。管理員可在 /config 將每則有效訊息的出現機率設為1%、5%、10%、15%或20%。\n"
            "- 最先點擊「捕獲棉花棒」的人獲得棉花棒；之後的點擊不得分。\n"
            "- 普通：47%，+1分。\n- 銀：14%，+2分。\n- 金：10%，+3分。\n"
            "- 瞬逝：7%，+5分，一分鐘後失效。\n"
            "- 神秘：7%，將其他一種類型隱藏20分鐘。若其中是瞬逝棉花棒，+5分在一分鐘後失效；之後以0分揭曉。\n"
            "- 腐爛：5%，偽裝成普通、銀、金或鑽石，捕獲時扣2分。\n"
            "- 放射性：4%，第0-4分鐘為-3分，5-9分鐘-1分，10-14分鐘+2分，15-17分鐘+4分，18-19分鐘+6分。\n"
            "- 假：3%，偽裝出現，價值0分，不安排下一次出現。\n"
            "- 雙生：2%，+4分，立刻再生成一根，並安排次日一根。\n"
            "- 鑽石：1%，+10分。\n"
            "- 若無人捕獲，棉花棒會失效，不扣任何人的分。普通棉花棒20分鐘失效，直接出現的瞬逝棉花棒一分鐘失效。分數可以為負。\n"
            "- 每次有效捕獲都會安排次日出現，但假棉花棒和超過一分鐘的隱藏瞬逝棉花棒除外。\n"
            "- /hisopos 顯示本群排行榜。"
        ),
    },
}

HISOPO_COOPERATIVE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "hisopos.type.giant": "hisopo gigante cooperativo",
        "hisopos.type.miracle": "hisopo milagroso",
        "hisopos.appeared_giant": "¡Apareció un Hisopo gigante cooperativo!\nProgreso: {current}/{required} · Premio: {points} pt por participante",
        "hisopos.giant_help_button": "Ayudar a capturarlo ({current}/{required})",
        "hisopos.giant_progress_caption": "¡El grupo está capturando un Hisopo gigante!\nProgreso: {current}/{required} · Premio: {points} pt por participante",
        "hisopos.giant_joined_popup": "¡Ayudaste! Van {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Ya ayudaste con este Hisopo. Van {current}/{required}.",
        "hisopos.giant_completed_caption": "¡Hisopo gigante capturado! Cooperaron {participants} personas y cada una ganó {points} pt.",
        "hisopos.giant_completed_popup": "¡Lo lograron! Ganaste {points} pt.",
        "hisopos.giant_rotten_caption": "El Hisopo gigante se pudrió con {current}/{required} ayudas. No se entregaron puntos.",
    },
    "en": {
        "hisopos.type.giant": "cooperative giant swab",
        "hisopos.type.miracle": "miracle swab",
        "hisopos.appeared_giant": "A cooperative Giant Swab appeared!\nProgress: {current}/{required} · Reward: {points} pt per participant",
        "hisopos.giant_help_button": "Help capture it ({current}/{required})",
        "hisopos.giant_progress_caption": "The group is capturing a Giant Swab!\nProgress: {current}/{required} · Reward: {points} pt per participant",
        "hisopos.giant_joined_popup": "You helped! Progress is {current}/{required}.",
        "hisopos.giant_already_joined_popup": "You already helped with this Swab. Progress is {current}/{required}.",
        "hisopos.giant_completed_caption": "Giant Swab captured! {participants} people cooperated and each earned {points} pt.",
        "hisopos.giant_completed_popup": "You did it! You earned {points} pt.",
        "hisopos.giant_rotten_caption": "The Giant Swab rotted at {current}/{required} helpers. No points were awarded.",
    },
    "es_ES": {
        "hisopos.type.giant": "hisopo gigante cooperativo",
        "hisopos.type.miracle": "hisopo milagroso",
        "hisopos.appeared_giant": "¡Ha aparecido un Hisopo gigante cooperativo!\nProgreso: {current}/{required} · Premio: {points} pt por participante",
        "hisopos.giant_help_button": "Ayudar a capturarlo ({current}/{required})",
        "hisopos.giant_progress_caption": "¡El grupo está capturando un Hisopo gigante!\nProgreso: {current}/{required} · Premio: {points} pt por participante",
        "hisopos.giant_joined_popup": "¡Has ayudado! Van {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Ya has ayudado con este Hisopo. Van {current}/{required}.",
        "hisopos.giant_completed_caption": "¡Hisopo gigante capturado! Han cooperado {participants} personas y cada una ha ganado {points} pt.",
        "hisopos.giant_completed_popup": "¡Lo habéis logrado! Has ganado {points} pt.",
        "hisopos.giant_rotten_caption": "El Hisopo gigante se pudrió con {current}/{required} ayudas. No se entregaron puntos.",
    },
    "ca": {
        "hisopos.type.giant": "bastonet gegant cooperatiu",
        "hisopos.type.miracle": "bastonet miraculós",
        "hisopos.appeared_giant": "Ha aparegut un Bastonet gegant cooperatiu!\nProgrés: {current}/{required} · Premi: {points} pt per participant",
        "hisopos.giant_help_button": "Ajuda a capturar-lo ({current}/{required})",
        "hisopos.giant_progress_caption": "El grup està capturant un Bastonet gegant!\nProgrés: {current}/{required} · Premi: {points} pt per participant",
        "hisopos.giant_joined_popup": "Hi has ajudat! Van {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Ja has ajudat amb aquest bastonet. Van {current}/{required}.",
        "hisopos.giant_completed_caption": "Bastonet gegant capturat! Hi han cooperat {participants} persones i cadascuna ha guanyat {points} pt.",
        "hisopos.giant_completed_popup": "Ho heu aconseguit! Has guanyat {points} pt.",
        "hisopos.giant_rotten_caption": "El Bastonet gegant s'ha podrit amb {current}/{required} ajudes. No s'han donat punts.",
    },
    "de": {
        "hisopos.type.giant": "kooperatives Riesen-Wattestäbchen",
        "hisopos.type.miracle": "Wunder-Wattestäbchen",
        "hisopos.appeared_giant": "Ein kooperatives Riesen-Wattestäbchen ist erschienen!\nFortschritt: {current}/{required} · Belohnung: {points} Pkt. pro Person",
        "hisopos.giant_help_button": "Beim Fangen helfen ({current}/{required})",
        "hisopos.giant_progress_caption": "Die Gruppe fängt ein Riesen-Wattestäbchen!\nFortschritt: {current}/{required} · Belohnung: {points} Pkt. pro Person",
        "hisopos.giant_joined_popup": "Du hast geholfen! Stand: {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Du hast schon geholfen. Stand: {current}/{required}.",
        "hisopos.giant_completed_caption": "Riesen-Wattestäbchen gefangen! {participants} Personen halfen und erhielten je {points} Pkt.",
        "hisopos.giant_completed_popup": "Geschafft! Du erhältst {points} Pkt.",
        "hisopos.giant_rotten_caption": "Das Riesen-Wattestäbchen verrottete bei {current}/{required} Helfern. Es gab keine Punkte.",
    },
    "eu": {
        "hisopos.type.giant": "kotoi-zotz erraldoi kooperatiboa",
        "hisopos.type.miracle": "kotoi-zotz miragarria",
        "hisopos.appeared_giant": "Kotoi-zotz erraldoi kooperatibo bat agertu da!\nAurrerapena: {current}/{required} · Saria: {points} puntu parte-hartzaileko",
        "hisopos.giant_help_button": "Lagundu harrapatzen ({current}/{required})",
        "hisopos.giant_progress_caption": "Taldea kotoi-zotz erraldoia harrapatzen ari da!\nAurrerapena: {current}/{required} · Saria: {points} puntu parte-hartzaileko",
        "hisopos.giant_joined_popup": "Lagundu duzu! {current}/{required} doaz.",
        "hisopos.giant_already_joined_popup": "Dagoeneko lagundu duzu. {current}/{required} doaz.",
        "hisopos.giant_completed_caption": "Kotoi-zotz erraldoia harrapatuta! {participants} lagunek parte hartu dute eta bakoitzak {points} puntu irabazi ditu.",
        "hisopos.giant_completed_popup": "Lortu duzue! {points} puntu irabazi dituzu.",
        "hisopos.giant_rotten_caption": "Kotoi-zotz erraldoia usteldu da {current}/{required} laguntzarekin. Ez da punturik eman.",
    },
    "fr": {
        "hisopos.type.giant": "coton-tige géant coopératif",
        "hisopos.type.miracle": "coton-tige miraculeux",
        "hisopos.appeared_giant": "Un Coton-tige géant coopératif est apparu !\nProgression : {current}/{required} · Gain : {points} pt par participant",
        "hisopos.giant_help_button": "Aider à le capturer ({current}/{required})",
        "hisopos.giant_progress_caption": "Le groupe capture un Coton-tige géant !\nProgression : {current}/{required} · Gain : {points} pt par participant",
        "hisopos.giant_joined_popup": "Tu as aidé ! Progression : {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Tu as déjà aidé. Progression : {current}/{required}.",
        "hisopos.giant_completed_caption": "Coton-tige géant capturé ! {participants} personnes ont coopéré et gagné {points} pt chacune.",
        "hisopos.giant_completed_popup": "Réussi ! Tu gagnes {points} pt.",
        "hisopos.giant_rotten_caption": "Le Coton-tige géant a pourri à {current}/{required} aides. Aucun point attribué.",
    },
    "gn": {
        "hisopos.type.giant": "hisopo tuicha joajúva",
        "hisopos.type.miracle": "hisopo hechapyrãva",
        "hisopos.appeared_giant": "Ojekuaa peteĩ Hisopo tuicha joajúva!\nJejapo: {current}/{required} · Jopói: {points} kyta peteĩteĩme",
        "hisopos.giant_help_button": "Eipytyvõ ojejapyhy hag̃ua ({current}/{required})",
        "hisopos.giant_progress_caption": "Aty ojapyhy hína peteĩ Hisopo tuicháva!\nJejapo: {current}/{required} · Jopói: {points} kyta peteĩteĩme",
        "hisopos.giant_joined_popup": "Reipytyvõma! Oho {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Reipytyvõma ko hisópope. Oho {current}/{required}.",
        "hisopos.giant_completed_caption": "Hisopo tuicha ojejapyhy! {participants} tapicha oñopytyvõ ha peteĩteĩ ohupyty {points} kyta.",
        "hisopos.giant_completed_popup": "Pejapóma! Rehupyty {points} kyta.",
        "hisopos.giant_rotten_caption": "Hisopo tuicha oñembyai {current}/{required} pytyvõ reheve. Ndoñeme'ẽi kyta.",
    },
    "it": {
        "hisopos.type.giant": "cotton fioc gigante cooperativo",
        "hisopos.type.miracle": "cotton fioc miracoloso",
        "hisopos.appeared_giant": "È apparso un Cotton fioc gigante cooperativo!\nProgresso: {current}/{required} · Premio: {points} pt per partecipante",
        "hisopos.giant_help_button": "Aiuta a catturarlo ({current}/{required})",
        "hisopos.giant_progress_caption": "Il gruppo sta catturando un Cotton fioc gigante!\nProgresso: {current}/{required} · Premio: {points} pt per partecipante",
        "hisopos.giant_joined_popup": "Hai aiutato! Siete a {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Hai già aiutato. Siete a {current}/{required}.",
        "hisopos.giant_completed_caption": "Cotton fioc gigante catturato! Hanno cooperato {participants} persone, ottenendo {points} pt ciascuna.",
        "hisopos.giant_completed_popup": "Ce l'avete fatta! Hai guadagnato {points} pt.",
        "hisopos.giant_rotten_caption": "Il Cotton fioc gigante è marcito con {current}/{required} aiuti. Nessun punto assegnato.",
    },
    "ja": {
        "hisopos.type.giant": "協力型巨大綿棒",
        "hisopos.type.miracle": "奇跡の綿棒",
        "hisopos.appeared_giant": "協力型巨大綿棒が現れた！\n進捗：{current}/{required}・報酬：参加者1人につき{points}点",
        "hisopos.giant_help_button": "捕獲を手伝う（{current}/{required}）",
        "hisopos.giant_progress_caption": "グループで巨大綿棒を捕獲中！\n進捗：{current}/{required}・報酬：参加者1人につき{points}点",
        "hisopos.giant_joined_popup": "協力しました！現在{current}/{required}です。",
        "hisopos.giant_already_joined_popup": "すでに協力済みです。現在{current}/{required}です。",
        "hisopos.giant_completed_caption": "巨大綿棒を捕獲！{participants}人が協力し、全員が{points}点を獲得しました。",
        "hisopos.giant_completed_popup": "成功！{points}点を獲得しました。",
        "hisopos.giant_rotten_caption": "巨大綿棒は{current}/{required}人の時点で腐りました。得点はありません。",
    },
    "la": {
        "hisopos.type.giant": "bacillum giganteum cooperativum",
        "hisopos.type.miracle": "bacillum miraculosum",
        "hisopos.appeared_giant": "Bacillum giganteum cooperativum apparuit!\nProgressus: {current}/{required} · Praemium: {points} puncta cuique",
        "hisopos.giant_help_button": "Ad capturam adiuva ({current}/{required})",
        "hisopos.giant_progress_caption": "Grex bacillum giganteum capit!\nProgressus: {current}/{required} · Praemium: {points} puncta cuique",
        "hisopos.giant_joined_popup": "Adiuvis! Nunc {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Iam adiuvis. Nunc {current}/{required}.",
        "hisopos.giant_completed_caption": "Bacillum giganteum captum! {participants} homines cooperati sunt et quisque {points} puncta accepit.",
        "hisopos.giant_completed_popup": "Perfecistis! {points} puncta accepisti.",
        "hisopos.giant_rotten_caption": "Bacillum giganteum cum {current}/{required} auxiliis putruit. Nulla puncta data sunt.",
    },
    "nl": {
        "hisopos.type.giant": "coöperatief reuzenwattenstaafje",
        "hisopos.type.miracle": "wonderwattenstaafje",
        "hisopos.appeared_giant": "Er verscheen een coöperatief Reuzenwattenstaafje!\nVoortgang: {current}/{required} · Beloning: {points} pt per deelnemer",
        "hisopos.giant_help_button": "Help het vangen ({current}/{required})",
        "hisopos.giant_progress_caption": "De groep vangt een Reuzenwattenstaafje!\nVoortgang: {current}/{required} · Beloning: {points} pt per deelnemer",
        "hisopos.giant_joined_popup": "Je hebt geholpen! Stand: {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Je hebt al geholpen. Stand: {current}/{required}.",
        "hisopos.giant_completed_caption": "Reuzenwattenstaafje gevangen! {participants} mensen werkten samen en kregen elk {points} pt.",
        "hisopos.giant_completed_popup": "Gelukt! Je kreeg {points} pt.",
        "hisopos.giant_rotten_caption": "Het Reuzenwattenstaafje rotte bij {current}/{required} helpers. Er zijn geen punten gegeven.",
    },
    "pt_BR": {
        "hisopos.type.giant": "cotonete gigante cooperativo",
        "hisopos.type.miracle": "cotonete milagroso",
        "hisopos.appeared_giant": "Apareceu um Cotonete gigante cooperativo!\nProgresso: {current}/{required} · Prêmio: {points} pt por participante",
        "hisopos.giant_help_button": "Ajudar a capturar ({current}/{required})",
        "hisopos.giant_progress_caption": "O grupo está capturando um Cotonete gigante!\nProgresso: {current}/{required} · Prêmio: {points} pt por participante",
        "hisopos.giant_joined_popup": "Você ajudou! Estão em {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Você já ajudou. Estão em {current}/{required}.",
        "hisopos.giant_completed_caption": "Cotonete gigante capturado! {participants} pessoas cooperaram e cada uma ganhou {points} pt.",
        "hisopos.giant_completed_popup": "Conseguiram! Você ganhou {points} pt.",
        "hisopos.giant_rotten_caption": "O Cotonete gigante apodreceu com {current}/{required} ajudas. Ninguém ganhou pontos.",
    },
    "pt_PT": {
        "hisopos.type.giant": "cotonete gigante cooperativo",
        "hisopos.type.miracle": "cotonete milagroso",
        "hisopos.appeared_giant": "Apareceu um Cotonete gigante cooperativo!\nProgresso: {current}/{required} · Prémio: {points} pt por participante",
        "hisopos.giant_help_button": "Ajudar a capturar ({current}/{required})",
        "hisopos.giant_progress_caption": "O grupo está a capturar um Cotonete gigante!\nProgresso: {current}/{required} · Prémio: {points} pt por participante",
        "hisopos.giant_joined_popup": "Ajudaste! Estão em {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Já ajudaste. Estão em {current}/{required}.",
        "hisopos.giant_completed_caption": "Cotonete gigante capturado! {participants} pessoas cooperaram e cada uma ganhou {points} pt.",
        "hisopos.giant_completed_popup": "Conseguiram! Ganhaste {points} pt.",
        "hisopos.giant_rotten_caption": "O Cotonete gigante apodreceu com {current}/{required} ajudas. Ninguém ganhou pontos.",
    },
    "quz": {
        "hisopos.type.giant": "yanapanakuspa hatun hisopo",
        "hisopos.type.miracle": "milagroso hisopo",
        "hisopos.appeared_giant": "Yanapanakuspa Hatun hisopo rikurimun!\nÑawpaqman: {current}/{required} · Quykuy: sapanka runapaq {points} puntu",
        "hisopos.giant_help_button": "Hap'iyta yanapay ({current}/{required})",
        "hisopos.giant_progress_caption": "Huñunakuy Hatun hisopota hap'ichkan!\nÑawpaqman: {current}/{required} · Quykuy: sapanka runapaq {points} puntu",
        "hisopos.giant_joined_popup": "Yanaparqanki! {current}/{required} kachkan.",
        "hisopos.giant_already_joined_popup": "Ñam yanaparqankña. {current}/{required} kachkan.",
        "hisopos.giant_completed_caption": "Hatun hisopo hap'isqa! {participants} runakuna yanapanakuspa sapanka {points} puntuta chaskirqanku.",
        "hisopos.giant_completed_popup": "Atirqankichik! {points} puntuta chaskirqanki.",
        "hisopos.giant_rotten_caption": "Hatun hisopo {current}/{required} yanapaywan ismurqan. Mana puntuta qukurqanchu.",
    },
    "ru": {
        "hisopos.type.giant": "кооперативная гигантская палочка",
        "hisopos.type.miracle": "чудесная ватная палочка",
        "hisopos.appeared_giant": "Появилась кооперативная Гигантская палочка!\nПрогресс: {current}/{required} · Награда: {points} очк. каждому",
        "hisopos.giant_help_button": "Помочь поймать ({current}/{required})",
        "hisopos.giant_progress_caption": "Группа ловит Гигантскую палочку!\nПрогресс: {current}/{required} · Награда: {points} очк. каждому",
        "hisopos.giant_joined_popup": "Вы помогли! Сейчас {current}/{required}.",
        "hisopos.giant_already_joined_popup": "Вы уже помогли. Сейчас {current}/{required}.",
        "hisopos.giant_completed_caption": "Гигантская палочка поймана! {participants} участников получили по {points} очк.",
        "hisopos.giant_completed_popup": "Получилось! Вы получили {points} очк.",
        "hisopos.giant_rotten_caption": "Гигантская палочка сгнила при {current}/{required} помощниках. Очки не начислены.",
    },
    "zh_Hans": {
        "hisopos.type.giant": "合作巨型棉签",
        "hisopos.type.miracle": "奇迹棉签",
        "hisopos.appeared_giant": "合作巨型棉签出现了！\n进度：{current}/{required} · 奖励：每位参与者{points}分",
        "hisopos.giant_help_button": "协助捕获（{current}/{required}）",
        "hisopos.giant_progress_caption": "本群正在捕获巨型棉签！\n进度：{current}/{required} · 奖励：每位参与者{points}分",
        "hisopos.giant_joined_popup": "你已协助！当前{current}/{required}。",
        "hisopos.giant_already_joined_popup": "你已经协助过了。当前{current}/{required}。",
        "hisopos.giant_completed_caption": "巨型棉签捕获成功！{participants}人合作，每人获得{points}分。",
        "hisopos.giant_completed_popup": "成功了！你获得{points}分。",
        "hisopos.giant_rotten_caption": "巨型棉签在{current}/{required}人时腐烂了，没有分数奖励。",
    },
    "zh_Hant": {
        "hisopos.type.giant": "合作巨型棉花棒",
        "hisopos.type.miracle": "奇蹟棉花棒",
        "hisopos.appeared_giant": "合作巨型棉花棒出現了！\n進度：{current}/{required} · 獎勵：每位參與者{points}分",
        "hisopos.giant_help_button": "協助捕獲（{current}/{required}）",
        "hisopos.giant_progress_caption": "本群正在捕獲巨型棉花棒！\n進度：{current}/{required} · 獎勵：每位參與者{points}分",
        "hisopos.giant_joined_popup": "你已協助！目前{current}/{required}。",
        "hisopos.giant_already_joined_popup": "你已經協助過了。目前{current}/{required}。",
        "hisopos.giant_completed_caption": "巨型棉花棒捕獲成功！{participants}人合作，每人獲得{points}分。",
        "hisopos.giant_completed_popup": "成功了！你獲得{points}分。",
        "hisopos.giant_rotten_caption": "巨型棉花棒在{current}/{required}人時腐爛了，沒有分數獎勵。",
    },
}

HISOPO_COOPERATIVE_RULE_UPDATES: dict[str, tuple[str, str, str]] = {
    "es": (
        "Común: 47 %",
        "Común: 46,65 %",
        "- Gigante cooperativo: 0,25 %, necesita hasta 15 participantes; en chats más pequeños necesita a todos los miembros disponibles. Cada persona ayuda una sola vez y, si lo completan dentro de 20 minutos, todos ganan +4 pt. Muestra el progreso; si estaba oculto por un Misterioso, la primera ayuda lo revela y cuenta.\n"
        "- Milagroso: 0,10 %, al capturarlo suma el mayor valor entre 15 pt y la mitad del puntaje del líder actual, redondeada hacia arriba, con un máximo de 1000 pt.",
    ),
    "en": (
        "Common: 47%",
        "Common: 46.65%",
        "- Cooperative Giant: 0.25%, requires up to 15 participants; smaller chats require every available member. Each person helps once and, if completed within 20 minutes, everyone earns +4 pt. Progress is shown; if hidden by a Mystery Swab, the first helper reveals it and counts.\n"
        "- Miracle: 0.10%; when captured, it awards the greater of 15 pt or half the current leader's score, rounded up, capped at 1000 pt.",
    ),
    "es_ES": (
        "Común: 47 %",
        "Común: 46,65 %",
        "- Gigante cooperativo: 0,25 %, necesita hasta 15 participantes; en chats más pequeños necesita a todos los miembros disponibles. Cada persona ayuda una sola vez y, si lo completan en 20 minutos, todos ganan +4 pt. Muestra el progreso; si estaba oculto por un Misterioso, la primera ayuda lo revela y cuenta.\n"
        "- Milagroso: 0,10 %; al capturarlo suma el mayor valor entre 15 pt y la mitad de la puntuación del líder actual, redondeada hacia arriba, con un máximo de 1000 pt.",
    ),
    "ca": (
        "Comú: 47 %",
        "Comú: 46,65 %",
        "- Gegant cooperatiu: 0,25 %, necessita fins a 15 participants; als xats més petits necessita tots els membres disponibles. Cada persona ajuda una sola vegada i, si el completen en 20 minuts, tothom guanya +4 pt. Mostra el progrés; si l'amagava un Misteriós, la primera ajuda el revela i compta.\n"
        "- Miraculós: 0,10 %; en capturar-lo dona el valor més alt entre 15 pt i la meitat de la puntuació del líder actual, arrodonida cap amunt, amb un màxim de 1000 pt.",
    ),
    "de": (
        "Gewöhnlich: 47 %",
        "Gewöhnlich: 46,65 %",
        "- Kooperativ riesig: 0,25 %, benötigt bis zu 15 Teilnehmende; in kleineren Chats alle verfügbaren Mitglieder. Jede Person hilft einmal. Bei Abschluss innerhalb von 20 Minuten erhalten alle +4 Pkt. Der Fortschritt ist sichtbar; war es im Mysteriösen verborgen, enthüllt und zählt die erste Hilfe.\n"
        "- Wunder: 0,10 %; beim Fangen gibt es den höheren Wert aus 15 Pkt. und der aufgerundeten Hälfte der aktuellen Führungspunktzahl, höchstens 1000 Pkt.",
    ),
    "eu": (
        "Arrunta: % 47",
        "Arrunta: % 46,65",
        "- Erraldoi kooperatiboa: % 0,25, gehienez 15 parte-hartzaile behar ditu; txat txikiagoetan, kide erabilgarri guztiak. Pertsona bakoitzak behin laguntzen du eta 20 minutuan osatuz gero denek +4 puntu lortzen dituzte. Aurrerapena ikusgai dago; Misteriotsu batek ezkutatzen bazuen, lehen laguntzak agerian uzten du eta zenbatzen du.\n"
        "- Miragarria: % 0,10; harrapatzean 15 puntu edo uneko liderraren puntuen erdia gorantz biribilduta ematen du, bietan handiena, gehienez 1000 puntu.",
    ),
    "fr": (
        "Commun : 47 %",
        "Commun : 46,65 %",
        "- Géant coopératif : 0,25 %, demande jusqu'à 15 participants ; dans les petits groupes, tous les membres disponibles. Chaque personne aide une fois et, s'il est terminé en 20 minutes, tous gagnent +4 pt. La progression est affichée ; s'il était caché par un Mystérieux, la première aide le révèle et compte.\n"
        "- Miraculeux : 0,10 % ; à la capture, rapporte le maximum entre 15 pt et la moitié arrondie au supérieur du score du leader actuel, dans la limite de 1000 pt.",
    ),
    "gn": (
        "Jepivegua: 47 %",
        "Jepivegua: 46,65 %",
        "- Tuichaitéva oñondive: 0,25 %, oikotevẽ 15 peve tapicha; aty michĩvape, opa tapicha oĩva. Peteĩteĩ oipytyvõ peteĩ jevy ha, ojapopa ramo 20 aravo'i ryepýpe, opavave ohupyty +4 kyta. Ojehechauka mba'éichapa oho; Ojekuaa'ỹva omokañýrõ, pe pytyvõ peteĩha ohechauka ha oñeipapa.\n"
        "- Marangatu: 0,10 %; ojejapyhy jave ome'ẽ pe tuichavéva 15 kyta térã mburuvicha ag̃agua kytakuéra mbyte, ojere yvate gotyo, ha 1000 kyta peve.",
    ),
    "it": (
        "Comune: 47 %",
        "Comune: 46,65 %",
        "- Gigante cooperativo: 0,25 %, richiede fino a 15 partecipanti; nelle chat più piccole servono tutti i membri disponibili. Ogni persona aiuta una volta e, se viene completato entro 20 minuti, tutti guadagnano +4 pt. Mostra i progressi; se era nascosto da un Misterioso, il primo aiuto lo rivela e conta.\n"
        "- Miracoloso: 0,10 %; alla cattura assegna il maggiore tra 15 pt e metà, arrotondata per eccesso, del punteggio del leader attuale, fino a un massimo di 1000 pt.",
    ),
    "ja": (
        "通常：47%",
        "通常：46.65%",
        "- 協力型巨大：0.25%。最大15人が必要で、より小さいチャットでは参加可能な全メンバーが必要です。各自1回だけ協力でき、20分以内に完成すると全員が+4点を獲得します。進捗を表示し、ミステリーに隠れていた場合は最初の協力で正体が明かされ、その1人も数えます。\n"
        "- 奇跡：0.10%。捕獲時に15点と、現在の首位得点の半分を切り上げた値のうち、大きい方を獲得し、上限は1000点です。",
    ),
    "la": (
        "Commune: 47 %",
        "Commune: 46,65 %",
        "- Gigante cooperativum: 0,25 %, usque ad 15 participes requirit; in gregibus minoribus omnes sodales praesentes. Quisque semel adiuvat et, si intra 20 minuta completur, omnes +4 puncta accipiunt. Progressus ostenditur; si a Mysterioso celabatur, primum auxilium id revelat et numeratur.\n"
        "- Miraculosum: 0,10 %; captum maius praemium dat inter 15 puncta et dimidiam partem, sursum rotundatam, punctorum ducis praesentis, summo 1000 punctorum.",
    ),
    "nl": (
        "Gewoon: 47%",
        "Gewoon: 46,65%",
        "- Coöperatieve reus: 0,25%, vereist maximaal 15 deelnemers; in kleinere chats alle beschikbare leden. Iedereen helpt één keer en als hij binnen 20 minuten voltooid wordt, krijgt iedereen +4 pt. De voortgang is zichtbaar; zat hij in een Mysterieus wattenstaafje, dan onthult en telt de eerste hulp.\n"
        "- Wonderbaarlijk: 0,10%; bij vangst geeft het de hoogste waarde van 15 pt of de naar boven afgeronde helft van de score van de huidige leider, tot maximaal 1000 pt.",
    ),
    "pt_BR": (
        "Comum: 47%",
        "Comum: 46,65%",
        "- Gigante cooperativo: 0,25%, exige até 15 participantes; em chats menores, todos os membros disponíveis. Cada pessoa ajuda uma vez e, se concluírem em 20 minutos, todos ganham +4 pt. O progresso aparece; se estava oculto por um Misterioso, a primeira ajuda o revela e conta.\n"
        "- Milagroso: 0,10%; ao capturar, concede o maior valor entre 15 pt e metade, arredondada para cima, da pontuação do líder atual, limitado a 1000 pt.",
    ),
    "pt_PT": (
        "Comum: 47 %",
        "Comum: 46,65 %",
        "- Gigante cooperativo: 0,25 %, exige até 15 participantes; em chats menores, todos os membros disponíveis. Cada pessoa ajuda uma vez e, se o concluírem em 20 minutos, todos ganham +4 pt. O progresso é mostrado; se estava oculto por um Misterioso, a primeira ajuda revela-o e conta.\n"
        "- Milagroso: 0,10 %; ao capturar, concede o maior valor entre 15 pt e metade, arredondada para cima, da pontuação do líder atual, limitado a 1000 pt.",
    ),
    "quz": (
        "Sapsi: 47 %",
        "Sapsi: 46,65 %",
        "- Hatun yanapanakuy: 0,25 %, 15 kama runakunata munan; aswan uchuy huñunakuykunapi, llapan tarikuq runakunata. Sapa runa huk kutilla yanapan, 20 minutopi tukuchiptinku llapanku +4 puntu chaskinku. Ñawpaqman riyta rikuchin; Pakasqa ukhunpi kashaptin, ñawpaq yanapakuq rikurichin hinaspa yupakun.\n"
        "- Milagroso: 0,10 %; hap'iptin 15 puntuwan kunan ñawpaq kaqpa puntunpa kuskanmanta wichayman muyuchisqawan tupachin, aswan hatunta qun, 1000 puntu kama.",
    ),
    "ru": (
        "Обычная: 47 %",
        "Обычная: 46,65 %",
        "- Кооперативная гигантская: 0,25 %, требует до 15 участников; в меньших чатах — всех доступных участников. Каждый помогает один раз. Если завершить за 20 минут, все получают +4 очка. Прогресс виден; если она скрыта в Таинственной, первая помощь раскрывает её и засчитывается.\n"
        "- Чудесная: 0,10 %; при поимке даёт большее из 15 очков и половины текущего счёта лидера с округлением вверх, но не более 1000 очков.",
    ),
    "zh_Hans": (
        "普通：47%",
        "普通：46.65%",
        "- 合作巨型：0.25%，最多需要15人；较小的群组需要所有可参与成员。每人只能协助一次，若在20分钟内完成，所有人各得+4分。消息会显示进度；若藏在神秘棉签中，首次协助会揭晓并计入人数。\n"
        "- 奇迹：0.10%，捕获时获得15分与当前领先者分数一半向上取整两者中的较大值，上限为1000分。",
    ),
    "zh_Hant": (
        "普通：47%",
        "普通：46.65%",
        "- 合作巨型：0.25%，最多需要15人；較小的群組需要所有可參與成員。每人只能協助一次，若在20分鐘內完成，所有人各得+4分。訊息會顯示進度；若藏在神秘棉花棒中，首次協助會揭曉並計入人數。\n"
        "- 奇蹟：0.10%，捕獲時獲得15分與目前領先者分數一半無條件進位兩者中的較大值，上限為1000分。",
    ),
}

HISOPO_GIANT_COUNT_RULES: dict[str, str] = {
    "es": "- Meta del Gigante: usa el total de miembros que informa Telegram menos Galerazo, con un máximo de 15. Esa consulta no distingue personas de otros bots, así que en chats pequeños esos bots también cuentan.",
    "en": "- Giant target: it uses Telegram's reported member total minus Galerazo, capped at 15. That count does not distinguish people from other bots, so those bots also count in small chats.",
    "es_ES": "- Objetivo del Gigante: usa el total de miembros que indica Telegram menos Galerazo, con un máximo de 15. Ese recuento no distingue personas de otros bots, por lo que esos bots también cuentan en chats pequeños.",
    "ca": "- Objectiu del Gegant: usa el total de membres que informa Telegram menys Galerazo, amb un màxim de 15. Aquest recompte no distingeix persones d'altres bots, així que aquests bots també compten als xats petits.",
    "de": "- Ziel des Riesen: Es verwendet die von Telegram gemeldete Mitgliederzahl abzüglich Galerazo, höchstens 15. Diese Zählung unterscheidet Menschen nicht von anderen Bots; in kleinen Chats zählen diese Bots daher mit.",
    "eu": "- Erraldoiaren helburua: Telegramek emandako kide kopurua ken Galerazo erabiltzen du, gehienez 15. Zenbaketak ez ditu pertsonak eta beste botak bereizten; beraz, txat txikietan bot horiek ere zenbatzen dira.",
    "fr": "- Objectif du Géant : il utilise le nombre total de membres indiqué par Telegram moins Galerazo, avec un maximum de 15. Ce comptage ne distingue pas les personnes des autres bots, qui comptent donc aussi dans les petits groupes.",
    "gn": "- Tuichaitéva rembipota: oipuru Telegram omombe'úva tapicha atyguáva retakue, oipe'ávo Galerazo, ha 15 peve. Upe jepapa ndoikuaái tapicha ha ambue bot ojoavyha; upévare aty michĩvape umi bot avei ojepapa.",
    "it": "- Obiettivo del Gigante: usa il totale dei membri indicato da Telegram meno Galerazo, fino a un massimo di 15. Questo conteggio non distingue le persone dagli altri bot, quindi nelle chat piccole contano anche quei bot.",
    "ja": "- 巨大綿棒の目標人数：Telegramが報告するメンバー総数からGalerazoを1体引き、最大15人とします。この人数は人間と他のボットを区別しないため、小規模チャットでは他のボットも人数に含まれます。",
    "la": "- Meta Gigantis: numero sodalium a Telegram nuntiato, Galerazo detracto, utitur, summo 15. Hic numerus homines ab aliis automatibus non distinguit; itaque in gregibus minoribus illa quoque numerantur.",
    "nl": "- Doel van de Reus: gebruikt het door Telegram gemelde ledental min Galerazo, met een maximum van 15. Die telling maakt geen onderscheid tussen mensen en andere bots, dus in kleine chats tellen die bots ook mee.",
    "pt_BR": "- Meta do Gigante: usa o total de membros informado pelo Telegram menos o Galerazo, limitado a 15. Essa contagem não distingue pessoas de outros bots, então esses bots também contam em chats pequenos.",
    "pt_PT": "- Objetivo do Gigante: usa o total de membros indicado pelo Telegram menos o Galerazo, limitado a 15. Esta contagem não distingue pessoas de outros bots, por isso esses bots também contam em chats pequenos.",
    "quz": "- Hatun hisopopa munasqan: Telegrampa willasqan llapan huñu runakunamanta Galerazota qichuspa yupakun, 15 kama. Kay yupayqa runakunata huk botkunamanta mana rakiyta atinchu; chayrayku uchuy huñukunapi chay botkuna kuska yupakun.",
    "ru": "- Цель Гигантской палочки: используется число участников, указанное Telegram, минус Galerazo, но не более 15. Этот счётчик не отличает людей от других ботов, поэтому в маленьких чатах такие боты тоже учитываются.",
    "zh_Hans": "- 巨型棉签目标人数：采用 Telegram 报告的成员总数减去 Galerazo，最多为15。该计数无法区分真人和其他机器人，因此小群中的其他机器人也会计入。",
    "zh_Hant": "- 巨型棉花棒目標人數：採用 Telegram 回報的成員總數減去 Galerazo，最多為15。此計數無法區分真人與其他機器人，因此小群組中的其他機器人也會計入。",
}

HISOPO_SCHEDULE_CAP_RULES: dict[str, str] = {
    "es": "- Agenda diaria: cada grupo puede acumular como máximo 10 apariciones con horario aleatorio para el día siguiente. El límite no afecta las apariciones activadas por mensajes ni la aparición inmediata del Gemelo.",
    "en": "- Daily schedule: each group can accumulate at most 10 random-time appearances for the next day. This limit does not affect message-triggered appearances or the Twin's immediate appearance.",
    "es_ES": "- Agenda diaria: cada grupo puede acumular como máximo 10 apariciones con horario aleatorio para el día siguiente. El límite no afecta a las apariciones activadas por mensajes ni a la aparición inmediata del Gemelo.",
    "ca": "- Agenda diària: cada grup pot acumular com a màxim 10 aparicions amb hora aleatòria per a l'endemà. El límit no afecta les aparicions activades per missatges ni l'aparició immediata del Bessó.",
    "de": "- Tagesplanung: Jede Gruppe kann höchstens 10 Erscheinungen zu zufälligen Uhrzeiten für den nächsten Tag sammeln. Das Limit betrifft weder durch Nachrichten ausgelöste Erscheinungen noch die sofortige Erscheinung des Zwillings.",
    "eu": "- Eguneko agenda: talde bakoitzak gehienez 10 agerpen meta ditzake hurrengo egunerako ausazko ordutegiarekin. Mugak ez die eragiten mezuek aktibatutako agerpenei, ezta Bikiaren berehalako agerpenari ere.",
    "fr": "- Programmation quotidienne : chaque groupe peut cumuler au maximum 10 apparitions à une heure aléatoire pour le lendemain. Cette limite ne concerne ni les apparitions déclenchées par les messages ni l'apparition immédiate du Jumeau.",
    "gn": "- Ára oúva ñemohenda: aty peteĩteĩ ikatu ombyaty 10 jehechauka peve aravo oñemoĩ rei hag̃ua ko'ẽrõ. Ko límite ndoikói ñe'ẽmondo omoñepyrũva jehechaukáre térã Kõi rehegua osẽ pya'évare.",
    "it": "- Programmazione giornaliera: ogni gruppo può accumulare al massimo 10 apparizioni a orario casuale per il giorno successivo. Il limite non riguarda le apparizioni attivate dai messaggi né l'apparizione immediata del Gemello.",
    "ja": "- 翌日の予約：各グループが翌日のランダムな時刻に予約できる出現は最大10回です。メッセージで発生する出現と、双子による即時出現はこの上限に含まれません。",
    "la": "- Ordinatio cotidiana: quisque grex summum 10 apparitiones hora fortuita in diem posterum servare potest. Hic finis neque apparitiones nuntiis excitatas neque statim a Gemino factam complectitur.",
    "nl": "- Dagplanning: elke groep kan maximaal 10 verschijningen op een willekeurig tijdstip voor de volgende dag verzamelen. De limiet geldt niet voor verschijningen door berichten of voor de onmiddellijke verschijning van de Tweeling.",
    "pt_BR": "- Agenda diária: cada grupo pode acumular no máximo 10 aparições em horários aleatórios para o dia seguinte. O limite não afeta aparições ativadas por mensagens nem a aparição imediata do Gêmeo.",
    "pt_PT": "- Agenda diária: cada grupo pode acumular no máximo 10 aparições em horários aleatórios para o dia seguinte. O limite não afeta as aparições ativadas por mensagens nem a aparição imediata do Gémeo.",
    "quz": "- Sapa p'unchawpa wakichiynin: sapa huñuqa paqarinpaq munasqa pachapi 10 rikurimuykunallatam wakichiyta atin. Kay tupuqa willakuykunamanta rikurimuqkunata ni Iskaypa chaylla rikurimuyninta hark'anchu.",
    "ru": "- Расписание на день: каждая группа может накопить не более 10 появлений в случайное время на следующий день. Лимит не относится к появлениям от сообщений и мгновенному появлению от Близнеца.",
    "zh_Hans": "- 次日安排：每个群组最多可累计10次安排在次日随机时刻的出现。此上限不影响由消息触发的出现，也不影响双生棉签立即触发的出现。",
    "zh_Hant": "- 次日安排：每個群組最多可累計10次安排在次日隨機時刻的出現。此上限不影響由訊息觸發的出現，也不影響雙生棉花棒立即觸發的出現。",
}

HISOPO_COLLECTION_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "help.coleccionhisopos": "muestra tu colección histórica de Hisopos",
        "hisopos.collection.header": "Colección histórica de {user} ({user_id})",
        "hisopos.collection.progress": "Tipos descubiertos: {discovered}/{total} · Capturas: {captures}",
    },
    "en": {
        "help.coleccionhisopos": "shows your historical Swab collection",
        "hisopos.collection.header": "Historical collection of {user} ({user_id})",
        "hisopos.collection.progress": "Types discovered: {discovered}/{total} · Captures: {captures}",
    },
    "es_ES": {
        "help.coleccionhisopos": "muestra tu colección histórica de Hisopos",
        "hisopos.collection.header": "Colección histórica de {user} ({user_id})",
        "hisopos.collection.progress": "Tipos descubiertos: {discovered}/{total} · Capturas: {captures}",
    },
    "ca": {
        "help.coleccionhisopos": "mostra la teva col·lecció històrica de Bastonets",
        "hisopos.collection.header": "Col·lecció històrica de {user} ({user_id})",
        "hisopos.collection.progress": "Tipus descoberts: {discovered}/{total} · Captures: {captures}",
    },
    "de": {
        "help.coleccionhisopos": "zeigt deine historische Wattestäbchen-Sammlung",
        "hisopos.collection.header": "Historische Sammlung von {user} ({user_id})",
        "hisopos.collection.progress": "Entdeckte Arten: {discovered}/{total} · Fänge: {captures}",
    },
    "eu": {
        "help.coleccionhisopos": "zure Kotoien bilduma historikoa erakusten du",
        "hisopos.collection.header": "{user} erabiltzailearen bilduma historikoa ({user_id})",
        "hisopos.collection.progress": "Aurkitutako motak: {discovered}/{total} · Harrapaketak: {captures}",
    },
    "fr": {
        "help.coleccionhisopos": "affiche votre collection historique de Cotons-tiges",
        "hisopos.collection.header": "Collection historique de {user} ({user_id})",
        "hisopos.collection.progress": "Types découverts : {discovered}/{total} · Captures : {captures}",
    },
    "gn": {
        "help.coleccionhisopos": "ohechauka nde Hisopo ñembyaty rembiasakue",
        "hisopos.collection.header": "{user} ñembyaty rembiasakue ({user_id})",
        "hisopos.collection.progress": "Peteĩchagua ojekuaáva: {discovered}/{total} · Ojejapyhýva: {captures}",
    },
    "it": {
        "help.coleccionhisopos": "mostra la tua collezione storica di Cotton Fioc",
        "hisopos.collection.header": "Collezione storica di {user} ({user_id})",
        "hisopos.collection.progress": "Tipi scoperti: {discovered}/{total} · Catture: {captures}",
    },
    "ja": {
        "help.coleccionhisopos": "綿棒の歴代コレクションを表示します",
        "hisopos.collection.header": "{user}（{user_id}）の歴代コレクション",
        "hisopos.collection.progress": "発見した種類：{discovered}/{total}・捕獲数：{captures}",
    },
    "la": {
        "help.coleccionhisopos": "collectionem historicam Bacillorum tuam ostendit",
        "hisopos.collection.header": "Collectio historica {user} ({user_id})",
        "hisopos.collection.progress": "Genera inventa: {discovered}/{total} · Capta: {captures}",
    },
    "nl": {
        "help.coleccionhisopos": "toont je historische Wattenstaafjescollectie",
        "hisopos.collection.header": "Historische collectie van {user} ({user_id})",
        "hisopos.collection.progress": "Ontdekte soorten: {discovered}/{total} · Gevangen: {captures}",
    },
    "pt_BR": {
        "help.coleccionhisopos": "mostra sua coleção histórica de Cotonetes",
        "hisopos.collection.header": "Coleção histórica de {user} ({user_id})",
        "hisopos.collection.progress": "Tipos descobertos: {discovered}/{total} · Capturas: {captures}",
    },
    "pt_PT": {
        "help.coleccionhisopos": "mostra a tua coleção histórica de Cotonetes",
        "hisopos.collection.header": "Coleção histórica de {user} ({user_id})",
        "hisopos.collection.progress": "Tipos descobertos: {discovered}/{total} · Capturas: {captures}",
    },
    "quz": {
        "help.coleccionhisopos": "hisopokunapa ñawpa huñusqaykita rikuchin",
        "hisopos.collection.header": "{user} runapa ñawpa huñusqan ({user_id})",
        "hisopos.collection.progress": "Riqsisqa laya: {discovered}/{total} · Hap'isqa: {captures}",
    },
    "ru": {
        "help.coleccionhisopos": "показывает вашу коллекцию палочек за всё время",
        "hisopos.collection.header": "Коллекция {user} за всё время ({user_id})",
        "hisopos.collection.progress": "Открыто видов: {discovered}/{total} · Поймано: {captures}",
    },
    "zh_Hans": {
        "help.coleccionhisopos": "显示你的历史棉签收藏",
        "hisopos.collection.header": "{user}（{user_id}）的历史收藏",
        "hisopos.collection.progress": "已发现种类：{discovered}/{total} · 捕获：{captures}",
    },
    "zh_Hant": {
        "help.coleccionhisopos": "顯示你的歷史棉花棒收藏",
        "hisopos.collection.header": "{user}（{user_id}）的歷史收藏",
        "hisopos.collection.progress": "已發現種類：{discovered}/{total} · 捕獲：{captures}",
    },
}

HISOPO_COLLECTION_RULES: dict[str, str] = {
    "es": "- Colección histórica: /coleccionhisopos muestra tus 12 tipos y sus cantidades. Cada Misterioso cuenta como Misterioso y como el tipo revelado; si ocultaba un Fugaz vencido, solo cuenta el Misterioso. Cada participante de un Gigante completado lo colecciona.",
    "en": "- Historical collection: /coleccionhisopos shows your 12 types and their counts. Each Mystery counts both as a Mystery and as the revealed type; if it hid an expired Fleeting, only the Mystery counts. Every participant collects a completed Giant.",
    "es_ES": "- Colección histórica: /coleccionhisopos muestra tus 12 tipos y sus cantidades. Cada Misterioso cuenta como Misterioso y como el tipo revelado; si ocultaba un Fugaz caducado, solo cuenta el Misterioso. Cada participante de un Gigante completado lo colecciona.",
    "ca": "- Col·lecció històrica: /coleccionhisopos mostra els teus 12 tipus i les quantitats. Cada Misteriós compta com a Misteriós i com el tipus revelat; si amagava un Fugaç caducat, només compta el Misteriós. Cada participant col·lecciona un Gegant completat.",
    "de": "- Historische Sammlung: /coleccionhisopos zeigt deine 12 Arten und ihre Anzahl. Jedes Mysteriöse zählt als Mysteriöses und als enthüllte Art; verbarg es ein abgelaufenes Flüchtiges, zählt nur das Mysteriöse. Alle Beteiligten sammeln einen vollendeten Riesen.",
    "eu": "- Bilduma historikoa: /coleccionhisopos komandoak zure 12 motak eta kopuruak erakusten ditu. Misteriotsu bakoitza Misteriotsu gisa eta agertutako mota gisa zenbatzen da; iraungitako Iheskor bat ezkutatzen bazuen, Misteriotsua bakarrik zenbatzen da. Amaitutako Erraldoiaren parte-hartzaile guztiek bilduman jasotzen dute.",
    "fr": "- Collection historique : /coleccionhisopos affiche vos 12 types et leurs quantités. Chaque Mystérieux compte comme Mystérieux et comme le type révélé ; s'il cachait un Fugace expiré, seul le Mystérieux compte. Chaque participant collectionne un Géant terminé.",
    "gn": "- Ñembyaty rembiasakue: /coleccionhisopos ohechauka 12 hisopo ha mboypa reguereko. Ñemi ojepapa Ñemíramo ha avei ohechaukáva hisóporamo; Pya'e kañymby oñembyaimava oguerekórõ, Ñemi añoite ojepapa. Tuichaitéva oñemohu'ãramo mayma oipytyvõva ombyaty.",
    "it": "- Collezione storica: /coleccionhisopos mostra i tuoi 12 tipi e le quantità. Ogni Misterioso conta sia come Misterioso sia come tipo rivelato; se nascondeva un Fugace scaduto, conta solo il Misterioso. Ogni partecipante colleziona un Gigante completato.",
    "ja": "- 歴代コレクション：/coleccionhisopos は12種類と所持数を表示します。ミステリーはミステリーと判明した種類の両方に数えます。期限切れの一瞬を隠していた場合はミステリーだけを数えます。巨大を完成させると参加者全員のコレクションに加わります。",
    "la": "- Collectio historica: /coleccionhisopos duodecim genera tua eorumque numeros ostendit. Quodque Mysteriosum et ut mysteriosum et pro genere revelato numeratur; si Fugitivum expletum celabat, solum Mysteriosum numeratur. Omnes participes Gigantem perfectum colligunt.",
    "nl": "- Historische collectie: /coleccionhisopos toont je 12 typen en aantallen. Elk Mysterie telt als Mysterie én als het onthulde type; verborg het een verlopen Vluchtige, dan telt alleen het Mysterie. Iedere deelnemer verzamelt een voltooide Reus.",
    "pt_BR": "- Coleção histórica: /coleccionhisopos mostra seus 12 tipos e as quantidades. Cada Misterioso conta como Misterioso e como o tipo revelado; se escondia um Fugaz vencido, só o Misterioso conta. Cada participante coleciona um Gigante concluído.",
    "pt_PT": "- Coleção histórica: /coleccionhisopos mostra os teus 12 tipos e as quantidades. Cada Misterioso conta como Misterioso e como o tipo revelado; se escondia um Fugaz expirado, só o Misterioso conta. Cada participante coleciona um Gigante concluído.",
    "quz": "- Ñawpa huñuy: /coleccionhisopos 12 layaykikunata, hayk'a kasqantawan rikuchin. Sapa Paka hisopoqa Paka hisopo hina, sut'inchasqan laya hinapas yupakun; pacha tukusqa Utqaqta pakarqan chayqa Paka hisopo sapallan yupakun. Hatun hisopota tukuchiq llapan yanapaqkunataq huñunku.",
    "ru": "- Коллекция за всё время: /coleccionhisopos показывает ваши 12 видов и их количество. Каждая Таинственная учитывается и как Таинственная, и как раскрытый вид; если внутри была просроченная Мимолётная, учитывается только Таинственная. Завершённая Гигантская попадает в коллекцию каждого участника.",
    "zh_Hans": "- 历史收藏：/coleccionhisopos 显示你的12种类型及数量。每根神秘棉签既按神秘棉签计入，也按揭晓的类型计入；若其中是已过期的迅捷棉签，则只计神秘棉签。完成巨型棉签时每位参与者都会收藏它。",
    "zh_Hant": "- 歷史收藏：/coleccionhisopos 顯示你的12種類型及數量。每根神祕棉花棒既按神祕棉花棒計入，也按揭曉的類型計入；若其中是已過期的迅捷棉花棒，則只計神祕棉花棒。完成巨型棉花棒時每位參與者都會收藏它。",
}

HISOPO_BOMB_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "hisopos.type.bomb": "hisopo bomba",
        "hisopos.collection.type.giant": "hisopo gigante",
        "hisopos.appeared_bomb": "¡Apareció un Hisopo bomba!\nElegí una casilla: una lo desactiva, otra lo hace explotar y las demás no hacen nada.",
        "hisopos.bomb_revealed_caption": "¡El Misterioso escondía un Hisopo bomba!\nElegí una casilla: una lo desactiva, otra lo hace explotar y las demás no hacen nada.",
        "hisopos.bomb_revealed_popup": "¡Era un Hisopo bomba! Ahora elegí una casilla.",
        "hisopos.bomb_miss_popup": "No desactivaste la bomba.",
        "hisopos.bomb_defused_caption": "{user} desactivó el Hisopo bomba y ganó {points} pt.",
        "hisopos.bomb_defused_popup": "¡Desactivaste la bomba! Ganaste {points} pt.",
        "hisopos.bomb_exploded_caption": "¡El Hisopo bomba le explotó a {user}! Perdió {points} pt.",
        "hisopos.bomb_exploded_popup": "¡Explotó la bomba! Perdiste {points} pt.",
    },
    "en": {
        "hisopos.type.bomb": "bomb swab",
        "hisopos.collection.type.giant": "giant swab",
        "hisopos.appeared_bomb": "A Bomb Swab appeared!\nPick a square: one defuses it, one detonates it, and the rest do nothing.",
        "hisopos.bomb_revealed_caption": "The Mystery hid a Bomb Swab!\nPick a square: one defuses it, one detonates it, and the rest do nothing.",
        "hisopos.bomb_revealed_popup": "It was a Bomb Swab! Now pick a square.",
        "hisopos.bomb_miss_popup": "You did not defuse the bomb.",
        "hisopos.bomb_defused_caption": "{user} defused the Bomb Swab and earned {points} pt.",
        "hisopos.bomb_defused_popup": "You defused the bomb! You earned {points} pt.",
        "hisopos.bomb_exploded_caption": "The Bomb Swab exploded on {user}! They lost {points} pt.",
        "hisopos.bomb_exploded_popup": "The bomb exploded! You lost {points} pt.",
    },
    "es_ES": {
        "hisopos.type.bomb": "hisopo bomba",
        "hisopos.collection.type.giant": "hisopo gigante",
        "hisopos.appeared_bomb": "¡Ha aparecido un Hisopo bomba!\nElige una casilla: una lo desactiva, otra lo hace explotar y las demás no hacen nada.",
        "hisopos.bomb_revealed_caption": "¡El Misterioso escondía un Hisopo bomba!\nElige una casilla: una lo desactiva, otra lo hace explotar y las demás no hacen nada.",
        "hisopos.bomb_revealed_popup": "¡Era un Hisopo bomba! Ahora elige una casilla.",
        "hisopos.bomb_miss_popup": "No has desactivado la bomba.",
        "hisopos.bomb_defused_caption": "{user} ha desactivado el Hisopo bomba y ha ganado {points} pt.",
        "hisopos.bomb_defused_popup": "¡Has desactivado la bomba! Has ganado {points} pt.",
        "hisopos.bomb_exploded_caption": "¡El Hisopo bomba le ha explotado a {user}! Ha perdido {points} pt.",
        "hisopos.bomb_exploded_popup": "¡La bomba ha explotado! Has perdido {points} pt.",
    },
    "ca": {
        "hisopos.type.bomb": "bastonet bomba",
        "hisopos.collection.type.giant": "bastonet gegant",
        "hisopos.appeared_bomb": "Ha aparegut un Bastonet bomba!\nTria una casella: una el desactiva, una el fa explotar i les altres no fan res.",
        "hisopos.bomb_revealed_caption": "El Misteriós amagava un Bastonet bomba!\nTria una casella: una el desactiva, una el fa explotar i les altres no fan res.",
        "hisopos.bomb_revealed_popup": "Era un Bastonet bomba! Ara tria una casella.",
        "hisopos.bomb_miss_popup": "No has desactivat la bomba.",
        "hisopos.bomb_defused_caption": "{user} ha desactivat el Bastonet bomba i ha guanyat {points} pt.",
        "hisopos.bomb_defused_popup": "Has desactivat la bomba! Has guanyat {points} pt.",
        "hisopos.bomb_exploded_caption": "El Bastonet bomba ha explotat a {user}! Ha perdut {points} pt.",
        "hisopos.bomb_exploded_popup": "La bomba ha explotat! Has perdut {points} pt.",
    },
    "de": {
        "hisopos.type.bomb": "Bomben-Wattestäbchen",
        "hisopos.collection.type.giant": "Riesen-Wattestäbchen",
        "hisopos.appeared_bomb": "Ein Bomben-Wattestäbchen ist erschienen!\nWähle ein Feld: Eines entschärft es, eines lässt es explodieren, die übrigen tun nichts.",
        "hisopos.bomb_revealed_caption": "Im Mysteriösen steckte ein Bomben-Wattestäbchen!\nWähle ein Feld: Eines entschärft es, eines lässt es explodieren, die übrigen tun nichts.",
        "hisopos.bomb_revealed_popup": "Es war ein Bomben-Wattestäbchen! Wähle jetzt ein Feld.",
        "hisopos.bomb_miss_popup": "Du hast die Bombe nicht entschärft.",
        "hisopos.bomb_defused_caption": "{user} hat das Bomben-Wattestäbchen entschärft und {points} Pkt. gewonnen.",
        "hisopos.bomb_defused_popup": "Bombe entschärft! Du erhältst {points} Pkt.",
        "hisopos.bomb_exploded_caption": "Das Bomben-Wattestäbchen ist bei {user} explodiert! {points} Pkt. verloren.",
        "hisopos.bomb_exploded_popup": "Die Bombe ist explodiert! Du verlierst {points} Pkt.",
    },
    "eu": {
        "hisopos.type.bomb": "bonba kotoi-zotza",
        "hisopos.collection.type.giant": "kotoi-zotz erraldoia",
        "hisopos.appeared_bomb": "Bonba kotoi-zotz bat agertu da!\nAukeratu laukia: batek indargabetzen du, batek leherrarazten du eta gainerakoek ez dute ezer egiten.",
        "hisopos.bomb_revealed_caption": "Misteriotsuak Bonba kotoi-zotz bat ezkutatzen zuen!\nAukeratu laukia: batek indargabetzen du, batek leherrarazten du eta gainerakoek ez dute ezer egiten.",
        "hisopos.bomb_revealed_popup": "Bonba kotoi-zotza zen! Aukeratu laukia.",
        "hisopos.bomb_miss_popup": "Ez duzu bonba indargabetu.",
        "hisopos.bomb_defused_caption": "{user} erabiltzaileak Bonba kotoi-zotza indargabetu eta {points} puntu irabazi ditu.",
        "hisopos.bomb_defused_popup": "Bonba indargabetu duzu! {points} puntu irabazi dituzu.",
        "hisopos.bomb_exploded_caption": "Bonba kotoi-zotza {user} erabiltzaileari lehertu zaio! {points} puntu galdu ditu.",
        "hisopos.bomb_exploded_popup": "Bonba lehertu da! {points} puntu galdu dituzu.",
    },
    "fr": {
        "hisopos.type.bomb": "coton-tige bombe",
        "hisopos.collection.type.giant": "coton-tige géant",
        "hisopos.appeared_bomb": "Un Coton-tige bombe est apparu !\nChoisissez une case : l'une le désamorce, l'une le fait exploser et les autres ne font rien.",
        "hisopos.bomb_revealed_caption": "Le Mystérieux cachait un Coton-tige bombe !\nChoisissez une case : l'une le désamorce, l'une le fait exploser et les autres ne font rien.",
        "hisopos.bomb_revealed_popup": "C'était un Coton-tige bombe ! Choisissez une case.",
        "hisopos.bomb_miss_popup": "Vous n'avez pas désamorcé la bombe.",
        "hisopos.bomb_defused_caption": "{user} a désamorcé le Coton-tige bombe et gagné {points} pt.",
        "hisopos.bomb_defused_popup": "Bombe désamorcée ! Vous gagnez {points} pt.",
        "hisopos.bomb_exploded_caption": "Le Coton-tige bombe a explosé sur {user} ! {points} pt perdus.",
        "hisopos.bomb_exploded_popup": "La bombe a explosé ! Vous perdez {points} pt.",
    },
    "gn": {
        "hisopos.type.bomb": "hisopo mbokapu",
        "hisopos.collection.type.giant": "hisopo tuicha",
        "hisopos.appeared_bomb": "Ojekuaa peteĩ Hisopo mbokapu!\nEiporavo peteĩ renda: peteĩ ombogue, ambue ombokapu ha umi ambuéva ndojapói mba'eve.",
        "hisopos.bomb_revealed_caption": "Ñemi omokañy peteĩ Hisopo mbokapu!\nEiporavo peteĩ renda: peteĩ ombogue, ambue ombokapu ha umi ambuéva ndojapói mba'eve.",
        "hisopos.bomb_revealed_popup": "Hisopo mbokapu ra'e! Eiporavo peteĩ renda.",
        "hisopos.bomb_miss_popup": "Neremboguéi pe mbokapu.",
        "hisopos.bomb_defused_caption": "{user} ombogue pe Hisopo mbokapu ha ohupyty {points} kyta.",
        "hisopos.bomb_defused_popup": "Rembogue pe mbokapu! Rehupyty {points} kyta.",
        "hisopos.bomb_exploded_caption": "Pe Hisopo mbokapu okapu {user} rehe! Oho chugui {points} kyta.",
        "hisopos.bomb_exploded_popup": "Pe mbokapu okapu! Oho ndehegui {points} kyta.",
    },
    "it": {
        "hisopos.type.bomb": "cotton fioc bomba",
        "hisopos.collection.type.giant": "cotton fioc gigante",
        "hisopos.appeared_bomb": "È apparso un Cotton fioc bomba!\nScegli una casella: una lo disinnesca, una lo fa esplodere e le altre non fanno nulla.",
        "hisopos.bomb_revealed_caption": "Il Misterioso nascondeva un Cotton fioc bomba!\nScegli una casella: una lo disinnesca, una lo fa esplodere e le altre non fanno nulla.",
        "hisopos.bomb_revealed_popup": "Era un Cotton fioc bomba! Ora scegli una casella.",
        "hisopos.bomb_miss_popup": "Non hai disinnescato la bomba.",
        "hisopos.bomb_defused_caption": "{user} ha disinnescato il Cotton fioc bomba e vinto {points} pt.",
        "hisopos.bomb_defused_popup": "Hai disinnescato la bomba! Hai vinto {points} pt.",
        "hisopos.bomb_exploded_caption": "Il Cotton fioc bomba è esploso a {user}! Ha perso {points} pt.",
        "hisopos.bomb_exploded_popup": "La bomba è esplosa! Hai perso {points} pt.",
    },
    "ja": {
        "hisopos.type.bomb": "爆弾綿棒",
        "hisopos.collection.type.giant": "巨大綿棒",
        "hisopos.appeared_bomb": "爆弾綿棒が現れた！\nマスを選んでください。1つは解除、1つは爆発、残りは何も起きません。",
        "hisopos.bomb_revealed_caption": "ミステリーの中身は爆弾綿棒だった！\nマスを選んでください。1つは解除、1つは爆発、残りは何も起きません。",
        "hisopos.bomb_revealed_popup": "爆弾綿棒でした！マスを選んでください。",
        "hisopos.bomb_miss_popup": "爆弾を解除できませんでした。",
        "hisopos.bomb_defused_caption": "{user}が爆弾綿棒を解除し、{points}点を獲得しました。",
        "hisopos.bomb_defused_popup": "爆弾解除成功！{points}点獲得しました。",
        "hisopos.bomb_exploded_caption": "爆弾綿棒が{user}のところで爆発！{points}点失いました。",
        "hisopos.bomb_exploded_popup": "爆弾が爆発！{points}点失いました。",
    },
    "la": {
        "hisopos.type.bomb": "bacillum pyrobolicum",
        "hisopos.collection.type.giant": "bacillum giganteum",
        "hisopos.appeared_bomb": "Bacillum pyrobolicum apparuit!\nLocum elige: unus id exarmat, unus displodit, ceteri nihil faciunt.",
        "hisopos.bomb_revealed_caption": "Mysteriosum Bacillum pyrobolicum celabat!\nLocum elige: unus id exarmat, unus displodit, ceteri nihil faciunt.",
        "hisopos.bomb_revealed_popup": "Bacillum pyrobolicum erat! Nunc locum elige.",
        "hisopos.bomb_miss_popup": "Pyrobolum non exarmavisti.",
        "hisopos.bomb_defused_caption": "{user} Bacillum pyrobolicum exarmavit et {points} puncta accepit.",
        "hisopos.bomb_defused_popup": "Pyrobolum exarmavisti! {points} puncta accepisti.",
        "hisopos.bomb_exploded_caption": "Bacillum pyrobolicum apud {user} displosit! {points} puncta amisit.",
        "hisopos.bomb_exploded_popup": "Pyrobolum displosit! {points} puncta amisisti.",
    },
    "nl": {
        "hisopos.type.bomb": "bomwattenstaafje",
        "hisopos.collection.type.giant": "reuzenwattenstaafje",
        "hisopos.appeared_bomb": "Er verscheen een Bomwattenstaafje!\nKies een vak: één ontmantelt het, één laat het ontploffen en de rest doet niets.",
        "hisopos.bomb_revealed_caption": "Het Mysterie verborg een Bomwattenstaafje!\nKies een vak: één ontmantelt het, één laat het ontploffen en de rest doet niets.",
        "hisopos.bomb_revealed_popup": "Het was een Bomwattenstaafje! Kies nu een vak.",
        "hisopos.bomb_miss_popup": "Je hebt de bom niet ontmanteld.",
        "hisopos.bomb_defused_caption": "{user} ontmantelde het Bomwattenstaafje en verdiende {points} pt.",
        "hisopos.bomb_defused_popup": "Bom ontmanteld! Je verdient {points} pt.",
        "hisopos.bomb_exploded_caption": "Het Bomwattenstaafje ontplofte bij {user}! {points} pt verloren.",
        "hisopos.bomb_exploded_popup": "De bom ontplofte! Je verliest {points} pt.",
    },
    "pt_BR": {
        "hisopos.type.bomb": "cotonete bomba",
        "hisopos.collection.type.giant": "cotonete gigante",
        "hisopos.appeared_bomb": "Apareceu um Cotonete bomba!\nEscolha uma casa: uma desarma, uma explode e as demais não fazem nada.",
        "hisopos.bomb_revealed_caption": "O Misterioso escondia um Cotonete bomba!\nEscolha uma casa: uma desarma, uma explode e as demais não fazem nada.",
        "hisopos.bomb_revealed_popup": "Era um Cotonete bomba! Agora escolha uma casa.",
        "hisopos.bomb_miss_popup": "Você não desarmou a bomba.",
        "hisopos.bomb_defused_caption": "{user} desarmou o Cotonete bomba e ganhou {points} pt.",
        "hisopos.bomb_defused_popup": "Você desarmou a bomba! Ganhou {points} pt.",
        "hisopos.bomb_exploded_caption": "O Cotonete bomba explodiu com {user}! Perdeu {points} pt.",
        "hisopos.bomb_exploded_popup": "A bomba explodiu! Você perdeu {points} pt.",
    },
    "pt_PT": {
        "hisopos.type.bomb": "cotonete bomba",
        "hisopos.collection.type.giant": "cotonete gigante",
        "hisopos.appeared_bomb": "Apareceu um Cotonete bomba!\nEscolhe uma casa: uma desarma-o, uma fá-lo explodir e as restantes não fazem nada.",
        "hisopos.bomb_revealed_caption": "O Misterioso escondia um Cotonete bomba!\nEscolhe uma casa: uma desarma-o, uma fá-lo explodir e as restantes não fazem nada.",
        "hisopos.bomb_revealed_popup": "Era um Cotonete bomba! Agora escolhe uma casa.",
        "hisopos.bomb_miss_popup": "Não desarmaste a bomba.",
        "hisopos.bomb_defused_caption": "{user} desarmou o Cotonete bomba e ganhou {points} pt.",
        "hisopos.bomb_defused_popup": "Desarmaste a bomba! Ganhaste {points} pt.",
        "hisopos.bomb_exploded_caption": "O Cotonete bomba explodiu com {user}! Perdeu {points} pt.",
        "hisopos.bomb_exploded_popup": "A bomba explodiu! Perdeste {points} pt.",
    },
    "quz": {
        "hisopos.type.bomb": "bomba hisopo",
        "hisopos.collection.type.giant": "hatun hisopo",
        "hisopos.appeared_bomb": "Bomba hisopo rikurimun!\nHuk tawkuta akllay: huknin wañuchin, huknin tuqyan, wakinkunaqa mana imatapas ruranchu.",
        "hisopos.bomb_revealed_caption": "Paka hisopoqa Bomba hisopota pakarqan!\nHuk tawkuta akllay: huknin wañuchin, huknin tuqyan, wakinkunaqa mana imatapas ruranchu.",
        "hisopos.bomb_revealed_popup": "Bomba hisopo karqan! Kunan huk tawkuta akllay.",
        "hisopos.bomb_miss_popup": "Bombata mana wañuchirqankichu.",
        "hisopos.bomb_defused_caption": "{user} Bomba hisopota wañuchispa {points} puntuta hap'irqan.",
        "hisopos.bomb_defused_popup": "Bombata wañuchirqanki! {points} puntuta hap'irqanki.",
        "hisopos.bomb_exploded_caption": "Bomba hisopo {user} runapa makimpi tuqyarqan! {points} puntuta chinkachirqan.",
        "hisopos.bomb_exploded_popup": "Bomba tuqyarqan! {points} puntuta chinkachirqanki.",
    },
    "ru": {
        "hisopos.type.bomb": "палочка-бомба",
        "hisopos.collection.type.giant": "гигантская палочка",
        "hisopos.appeared_bomb": "Появилась Палочка-бомба!\nВыберите ячейку: одна обезвредит её, одна взорвёт, остальные ничего не сделают.",
        "hisopos.bomb_revealed_caption": "В Таинственной скрывалась Палочка-бомба!\nВыберите ячейку: одна обезвредит её, одна взорвёт, остальные ничего не сделают.",
        "hisopos.bomb_revealed_popup": "Это была Палочка-бомба! Теперь выберите ячейку.",
        "hisopos.bomb_miss_popup": "Вы не обезвредили бомбу.",
        "hisopos.bomb_defused_caption": "{user} обезвредил Палочку-бомбу и получил {points} очков.",
        "hisopos.bomb_defused_popup": "Бомба обезврежена! Вы получили {points} очков.",
        "hisopos.bomb_exploded_caption": "Палочка-бомба взорвалась у {user}! Потеряно {points} очков.",
        "hisopos.bomb_exploded_popup": "Бомба взорвалась! Вы потеряли {points} очков.",
    },
    "zh_Hans": {
        "hisopos.type.bomb": "炸弹棉签",
        "hisopos.collection.type.giant": "巨型棉签",
        "hisopos.appeared_bomb": "炸弹棉签出现了！\n请选择一格：一格可拆弹，一格会爆炸，其余不会发生任何事。",
        "hisopos.bomb_revealed_caption": "神秘棉签里藏着炸弹棉签！\n请选择一格：一格可拆弹，一格会爆炸，其余不会发生任何事。",
        "hisopos.bomb_revealed_popup": "原来是炸弹棉签！现在请选择一格。",
        "hisopos.bomb_miss_popup": "你没有拆除炸弹。",
        "hisopos.bomb_defused_caption": "{user}拆除了炸弹棉签，获得{points}分。",
        "hisopos.bomb_defused_popup": "拆弹成功！你获得{points}分。",
        "hisopos.bomb_exploded_caption": "炸弹棉签在{user}手中爆炸！失去{points}分。",
        "hisopos.bomb_exploded_popup": "炸弹爆炸了！你失去{points}分。",
    },
    "zh_Hant": {
        "hisopos.type.bomb": "炸彈棉花棒",
        "hisopos.collection.type.giant": "巨型棉花棒",
        "hisopos.appeared_bomb": "炸彈棉花棒出現了！\n請選一格：一格可拆彈，一格會爆炸，其餘不會發生任何事。",
        "hisopos.bomb_revealed_caption": "神祕棉花棒裡藏著炸彈棉花棒！\n請選一格：一格可拆彈，一格會爆炸，其餘不會發生任何事。",
        "hisopos.bomb_revealed_popup": "原來是炸彈棉花棒！現在請選一格。",
        "hisopos.bomb_miss_popup": "你沒有拆除炸彈。",
        "hisopos.bomb_defused_caption": "{user}拆除了炸彈棉花棒，獲得{points}分。",
        "hisopos.bomb_defused_popup": "拆彈成功！你獲得{points}分。",
        "hisopos.bomb_exploded_caption": "炸彈棉花棒在{user}手中爆炸！失去{points}分。",
        "hisopos.bomb_exploded_popup": "炸彈爆炸了！你失去{points}分。",
    },
}

HISOPO_RACE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "hisopos.type.frenetic": "hisopo frenético",
        "hisopos.type.black_hole": "hisopo agujero negro",
        "hisopos.type.expired": "hisopo vencido",
        "hisopos.appeared_race": "¡Apareció un {type_label}!\nLa primera persona que llegue a {target} pulsaciones gana.",
        "hisopos.race_button": "Pulsar",
        "hisopos.race_press_popup": "Tu pulsación contó: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Esa pulsación fue demasiado rápida y no contó.",
        "hisopos.race_won_caption": "{user} ganó la carrera por el {type_label} y sumó {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} dominó en soledad el {type_label} y sumó {points} pt.",
        "hisopos.black_hole_won_caption": "{user} dominó el {type_label}: ganó {points} pt y absorbió {lost_points} pt de {rivals} rival(es).",
        "hisopos.race_won_popup": "¡Ganaste la carrera! Sumaste {points} pt.",
        "hisopos.expired_caption_collected": "Era un {type_label}. ¡Te lo perdiste! No suma puntos, pero descubriste un hisopo vencido.",
        "hisopos.expired_caption_mystery": "El Misterioso era un {type_label}. ¡Te lo perdiste! No suma puntos ni un hisopo vencido.",
        "hisopos.expired_popup_collected": "Llegaste tarde: no suma puntos, pero coleccionaste un hisopo vencido.",
        "hisopos.expired_popup_mystery": "Llegaste tarde. El Misterioso reveló su tipo, pero no suma puntos ni un hisopo vencido.",
    },
    "en": {
        "hisopos.type.frenetic": "frenetic swab",
        "hisopos.type.black_hole": "black-hole swab",
        "hisopos.type.expired": "expired swab",
        "hisopos.appeared_race": "A {type_label} appeared!\nThe first person to reach {target} presses wins.",
        "hisopos.race_button": "Press",
        "hisopos.race_press_popup": "Your press counted: {current}/{target}.",
        "hisopos.race_too_fast_popup": "That press was too fast and did not count.",
        "hisopos.race_won_caption": "{user} won the race for the {type_label} and earned {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} mastered the {type_label} alone and earned {points} pt.",
        "hisopos.black_hole_won_caption": "{user} mastered the {type_label}: {points} pt gained and {lost_points} pt absorbed from {rivals} rival(s).",
        "hisopos.race_won_popup": "You won the race! You earned {points} pt.",
        "hisopos.expired_caption_collected": "It was a {type_label}. You missed it! No points, but you discovered an expired swab.",
        "hisopos.expired_caption_mystery": "The Mystery was a {type_label}. You missed it! No points and no expired swab.",
        "hisopos.expired_popup_collected": "Too late: no points, but you collected an expired swab.",
        "hisopos.expired_popup_mystery": "Too late. The Mystery revealed its type, but gives no points or expired swab.",
    },
    "es_ES": {
        "hisopos.type.frenetic": "hisopo frenético",
        "hisopos.type.black_hole": "hisopo agujero negro",
        "hisopos.type.expired": "hisopo caducado",
        "hisopos.appeared_race": "¡Ha aparecido un {type_label}!\nLa primera persona que llegue a {target} pulsaciones gana.",
        "hisopos.race_button": "Pulsar",
        "hisopos.race_press_popup": "Tu pulsación ha contado: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Esa pulsación ha sido demasiado rápida y no ha contado.",
        "hisopos.race_won_caption": "{user} ha ganado la carrera por el {type_label} y ha sumado {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} ha dominado en solitario el {type_label} y ha sumado {points} pt.",
        "hisopos.black_hole_won_caption": "{user} ha dominado el {type_label}: ha ganado {points} pt y absorbido {lost_points} pt de {rivals} rival(es).",
        "hisopos.race_won_popup": "¡Has ganado la carrera! Has sumado {points} pt.",
        "hisopos.expired_caption_collected": "Era un {type_label}. ¡Te lo has perdido! No da puntos, pero has descubierto un hisopo caducado.",
        "hisopos.expired_caption_mystery": "El Misterioso era un {type_label}. ¡Te lo has perdido! No da puntos ni un hisopo caducado.",
        "hisopos.expired_popup_collected": "Has llegado tarde: no da puntos, pero has coleccionado un hisopo caducado.",
        "hisopos.expired_popup_mystery": "Has llegado tarde. El Misterioso reveló su tipo, pero no da puntos ni un hisopo caducado.",
    },
    "ca": {
        "hisopos.type.frenetic": "bastonet frenètic",
        "hisopos.type.black_hole": "bastonet forat negre",
        "hisopos.type.expired": "bastonet caducat",
        "hisopos.appeared_race": "Ha aparegut un {type_label}!\nLa primera persona que arribi a {target} pulsacions guanya.",
        "hisopos.race_button": "Prem",
        "hisopos.race_press_popup": "La pulsació ha comptat: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Aquesta pulsació ha estat massa ràpida i no ha comptat.",
        "hisopos.race_won_caption": "{user} ha guanyat la cursa pel {type_label} i ha sumat {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} ha dominat tot sol el {type_label} i ha sumat {points} pt.",
        "hisopos.black_hole_won_caption": "{user} ha dominat el {type_label}: ha guanyat {points} pt i absorbit {lost_points} pt de {rivals} rival(s).",
        "hisopos.race_won_popup": "Has guanyat la cursa! Has sumat {points} pt.",
        "hisopos.expired_caption_collected": "Era un {type_label}. L'has perdut! No dona punts, però has descobert un bastonet caducat.",
        "hisopos.expired_caption_mystery": "El Misteriós era un {type_label}. L'has perdut! No dona punts ni un bastonet caducat.",
        "hisopos.expired_popup_collected": "Has arribat tard: no dona punts, però has col·leccionat un bastonet caducat.",
        "hisopos.expired_popup_mystery": "Has arribat tard. El Misteriós revela el tipus, però no dona punts ni un bastonet caducat.",
    },
    "de": {
        "hisopos.type.frenetic": "Rasendes Wattestäbchen",
        "hisopos.type.black_hole": "Schwarzes-Loch-Wattestäbchen",
        "hisopos.type.expired": "Abgelaufenes Wattestäbchen",
        "hisopos.appeared_race": "Ein {type_label} ist erschienen!\nWer zuerst {target} Klicks erreicht, gewinnt.",
        "hisopos.race_button": "Drücken",
        "hisopos.race_press_popup": "Dein Klick zählt: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Dieser Klick war zu schnell und zählt nicht.",
        "hisopos.race_won_caption": "{user} gewinnt das Rennen um das {type_label} und erhält {points} Pkt.",
        "hisopos.black_hole_won_solo_caption": "{user} beherrscht das {type_label} allein und erhält {points} Pkt.",
        "hisopos.black_hole_won_caption": "{user} beherrscht das {type_label}: {points} Pkt. gewonnen und {lost_points} Pkt. von {rivals} Gegner(n) absorbiert.",
        "hisopos.race_won_popup": "Rennen gewonnen! Du erhältst {points} Pkt.",
        "hisopos.expired_caption_collected": "Es war ein {type_label}. Verpasst! Keine Punkte, aber du entdeckst ein abgelaufenes Wattestäbchen.",
        "hisopos.expired_caption_mystery": "Das Mysteriöse war ein {type_label}. Verpasst! Keine Punkte und kein abgelaufenes Wattestäbchen.",
        "hisopos.expired_popup_collected": "Zu spät: keine Punkte, aber ein abgelaufenes Wattestäbchen gesammelt.",
        "hisopos.expired_popup_mystery": "Zu spät. Das Mysteriöse enthüllt seine Art, gibt aber keine Punkte oder Sammlung.",
    },
    "eu": {
        "hisopos.type.frenetic": "kotoi-zotz frenetikoa",
        "hisopos.type.black_hole": "zulo beltzeko kotoi-zotza",
        "hisopos.type.expired": "iraungitako kotoi-zotza",
        "hisopos.appeared_race": "{type_label} bat agertu da!\n{target} sakatze lortzen duen lehenak irabaziko du.",
        "hisopos.race_button": "Sakatu",
        "hisopos.race_press_popup": "Sakatzea zenbatu da: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Sakatzea azkarregia izan da eta ez da zenbatu.",
        "hisopos.race_won_caption": "{user} erabiltzaileak {type_label} lortzeko lasterketa irabazi eta {points} puntu eskuratu ditu.",
        "hisopos.black_hole_won_solo_caption": "{user} erabiltzaileak bakarrik menderatu du {type_label} eta {points} puntu eskuratu ditu.",
        "hisopos.black_hole_won_caption": "{user} erabiltzaileak {type_label} menderatu du: {points} puntu irabazi, {lost_points} puntu xurgatu eta {rivals} arerio garaitu ditu.",
        "hisopos.race_won_popup": "Lasterketa irabazi duzu! {points} puntu eskuratu dituzu.",
        "hisopos.expired_caption_collected": "{type_label} bat zen. Galdu duzu! Ez du punturik ematen, baina iraungitako kotoi-zotza aurkitu duzu.",
        "hisopos.expired_caption_mystery": "Misteriotsua {type_label} bat zen. Galdu duzu! Ez du punturik edo iraungitakorik ematen.",
        "hisopos.expired_popup_collected": "Berandu: punturik ez, baina iraungitako kotoi-zotza bildu duzu.",
        "hisopos.expired_popup_mystery": "Berandu. Misteriotsuak mota erakutsi du, baina ez du punturik edo iraungitakorik ematen.",
    },
    "fr": {
        "hisopos.type.frenetic": "coton-tige frénétique",
        "hisopos.type.black_hole": "coton-tige trou noir",
        "hisopos.type.expired": "coton-tige expiré",
        "hisopos.appeared_race": "Un {type_label} est apparu !\nLa première personne à atteindre {target} pressions gagne.",
        "hisopos.race_button": "Appuyer",
        "hisopos.race_press_popup": "Votre pression compte : {current}/{target}.",
        "hisopos.race_too_fast_popup": "Cette pression était trop rapide et ne compte pas.",
        "hisopos.race_won_caption": "{user} gagne la course au {type_label} et reçoit {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} maîtrise seul le {type_label} et reçoit {points} pt.",
        "hisopos.black_hole_won_caption": "{user} maîtrise le {type_label} : {points} pt gagnés et {lost_points} pt absorbés à {rivals} adversaire(s).",
        "hisopos.race_won_popup": "Course gagnée ! Vous recevez {points} pt.",
        "hisopos.expired_caption_collected": "C'était un {type_label}. Trop tard ! Aucun point, mais vous découvrez un coton-tige expiré.",
        "hisopos.expired_caption_mystery": "Le Mystérieux était un {type_label}. Trop tard ! Aucun point ni coton-tige expiré.",
        "hisopos.expired_popup_collected": "Trop tard : aucun point, mais vous collectionnez un coton-tige expiré.",
        "hisopos.expired_popup_mystery": "Trop tard. Le Mystérieux révèle son type, sans point ni coton-tige expiré.",
    },
    "gn": {
        "hisopos.type.frenetic": "hisopo sarambi",
        "hisopos.type.black_hole": "hisopo kuára hũ",
        "hisopos.type.expired": "hisopo oñembyaíva",
        "hisopos.appeared_race": "Ojekuaa peteĩ {type_label}!\nOikóva tenonde {target} jopyhápe ogana.",
        "hisopos.race_button": "Ejopy",
        "hisopos.race_press_popup": "Nde jopyha ojepapa: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Pya'eterei rejopy ha ndojepapái.",
        "hisopos.race_won_caption": "{user} ogana {type_label} rehegua ñani ha ohupyty {points} kyta.",
        "hisopos.black_hole_won_solo_caption": "{user} añoite ipu'aka {type_label} rehe ha ohupyty {points} kyta.",
        "hisopos.black_hole_won_caption": "{user} ipu'aka {type_label} rehe: ohupyty {points} kyta ha omokõ {lost_points} kyta {rivals} oñaníva gui.",
        "hisopos.race_won_popup": "Regana pe ñani! Rehupyty {points} kyta.",
        "hisopos.expired_caption_collected": "Ha'e kuri {type_label}. Ndoguahẽi ndéve! Ndojapói kyta, hákatu rembyaty hisopo oñembyaíva.",
        "hisopos.expired_caption_mystery": "Ñemi ha'e kuri {type_label}. Ndoguahẽi ndéve! Ndojapói kyta ni hisopo oñembyaíva.",
        "hisopos.expired_popup_collected": "Reguahẽ tarde: ndaipóri kyta, hákatu rembyaty hisopo oñembyaíva.",
        "hisopos.expired_popup_mystery": "Reguahẽ tarde. Ñemi ohechauka imba'e, ndaipóri kyta ni hisopo oñembyaíva.",
    },
    "it": {
        "hisopos.type.frenetic": "cotton fioc frenetico",
        "hisopos.type.black_hole": "cotton fioc buco nero",
        "hisopos.type.expired": "cotton fioc scaduto",
        "hisopos.appeared_race": "È apparso un {type_label}!\nVince la prima persona che raggiunge {target} pressioni.",
        "hisopos.race_button": "Premi",
        "hisopos.race_press_popup": "La pressione conta: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Quella pressione era troppo rapida e non conta.",
        "hisopos.race_won_caption": "{user} ha vinto la corsa al {type_label} e guadagnato {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} ha dominato da solo il {type_label} e guadagnato {points} pt.",
        "hisopos.black_hole_won_caption": "{user} ha dominato il {type_label}: {points} pt guadagnati e {lost_points} pt assorbiti da {rivals} rivale/i.",
        "hisopos.race_won_popup": "Hai vinto la corsa! Hai guadagnato {points} pt.",
        "hisopos.expired_caption_collected": "Era un {type_label}. Te lo sei perso! Nessun punto, ma hai scoperto un cotton fioc scaduto.",
        "hisopos.expired_caption_mystery": "Il Misterioso era un {type_label}. Te lo sei perso! Nessun punto né cotton fioc scaduto.",
        "hisopos.expired_popup_collected": "Troppo tardi: nessun punto, ma hai collezionato un cotton fioc scaduto.",
        "hisopos.expired_popup_mystery": "Troppo tardi. Il Misterioso rivela il tipo, ma non dà punti né uno Scaduto.",
    },
    "ja": {
        "hisopos.type.frenetic": "熱狂綿棒",
        "hisopos.type.black_hole": "ブラックホール綿棒",
        "hisopos.type.expired": "期限切れ綿棒",
        "hisopos.appeared_race": "{type_label}が現れました！\n最初に{target}回押した人の勝ちです。",
        "hisopos.race_button": "押す",
        "hisopos.race_press_popup": "カウントされました：{current}/{target}。",
        "hisopos.race_too_fast_popup": "押すのが速すぎたためカウントされません。",
        "hisopos.race_won_caption": "{user}が{type_label}争奪戦に勝ち、{points}点を獲得しました。",
        "hisopos.black_hole_won_solo_caption": "{user}が単独で{type_label}を制し、{points}点を獲得しました。",
        "hisopos.black_hole_won_caption": "{user}が{type_label}を制覇！{points}点を得て、{lost_points}点を{rivals}人から吸収しました。",
        "hisopos.race_won_popup": "勝利！{points}点を獲得しました。",
        "hisopos.expired_caption_collected": "{type_label}でした。間に合いませんでした！得点はありませんが、期限切れ綿棒を発見しました。",
        "hisopos.expired_caption_mystery": "ミステリーの正体は{type_label}でした。間に合いませんでした！得点も期限切れ綿棒もありません。",
        "hisopos.expired_popup_collected": "時間切れです。得点はありませんが、期限切れ綿棒を収集しました。",
        "hisopos.expired_popup_mystery": "時間切れです。正体は判明しますが、得点も期限切れ綿棒もありません。",
    },
    "la": {
        "hisopos.type.frenetic": "bacillum freneticum",
        "hisopos.type.black_hole": "bacillum foraminis atri",
        "hisopos.type.expired": "bacillum expletum",
        "hisopos.appeared_race": "{type_label} apparuit!\nPrimus qui {target} pressiones attingit vincit.",
        "hisopos.race_button": "Preme",
        "hisopos.race_press_popup": "Pressio numerata est: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Pressio nimis celeris fuit neque numerata est.",
        "hisopos.race_won_caption": "{user} certamen pro {type_label} vicit et {points} puncta accepit.",
        "hisopos.black_hole_won_solo_caption": "{user} solus {type_label} vicit et {points} puncta accepit.",
        "hisopos.black_hole_won_caption": "{user} {type_label} vicit: {points} puncta cepit atque {lost_points} a {rivals} aemulo/aemulis hausit.",
        "hisopos.race_won_popup": "Certamen vicisti! {points} puncta accepisti.",
        "hisopos.expired_caption_collected": "{type_label} erat. Amisisti! Nulla puncta, sed bacillum expletum collegisti.",
        "hisopos.expired_caption_mystery": "Mysteriosum {type_label} erat. Amisisti! Nulla puncta neque bacillum expletum.",
        "hisopos.expired_popup_collected": "Serum venisti: nulla puncta, sed bacillum expletum collegisti.",
        "hisopos.expired_popup_mystery": "Serum venisti. Mysteriosum genus aperit, sed nulla puncta neque bacillum expletum dat.",
    },
    "nl": {
        "hisopos.type.frenetic": "razende wattenstaaf",
        "hisopos.type.black_hole": "zwartgat-wattenstaaf",
        "hisopos.type.expired": "verlopen wattenstaaf",
        "hisopos.appeared_race": "Er verscheen een {type_label}!\nDe eerste die {target} keer drukt, wint.",
        "hisopos.race_button": "Druk",
        "hisopos.race_press_popup": "Je druk telt: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Die druk was te snel en telt niet.",
        "hisopos.race_won_caption": "{user} won de race om de {type_label} en kreeg {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} beheerste alleen de {type_label} en kreeg {points} pt.",
        "hisopos.black_hole_won_caption": "{user} beheerste de {type_label}: {points} pt gewonnen en {lost_points} pt van {rivals} riva(a)l(en) geabsorbeerd.",
        "hisopos.race_won_popup": "Je won de race! Je kreeg {points} pt.",
        "hisopos.expired_caption_collected": "Het was een {type_label}. Gemist! Geen punten, maar wel een verlopen wattenstaaf ontdekt.",
        "hisopos.expired_caption_mystery": "Het Mysterie was een {type_label}. Gemist! Geen punten en geen verlopen wattenstaaf.",
        "hisopos.expired_popup_collected": "Te laat: geen punten, maar wel een verlopen wattenstaaf verzameld.",
        "hisopos.expired_popup_mystery": "Te laat. Het Mysterie onthult het type, maar geeft geen punten of verlopen wattenstaaf.",
    },
    "pt_BR": {
        "hisopos.type.frenetic": "cotonete frenético",
        "hisopos.type.black_hole": "cotonete buraco negro",
        "hisopos.type.expired": "cotonete vencido",
        "hisopos.appeared_race": "Apareceu um {type_label}!\nA primeira pessoa a chegar a {target} toques vence.",
        "hisopos.race_button": "Tocar",
        "hisopos.race_press_popup": "Seu toque contou: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Esse toque foi rápido demais e não contou.",
        "hisopos.race_won_caption": "{user} venceu a corrida pelo {type_label} e ganhou {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} dominou sozinho o {type_label} e ganhou {points} pt.",
        "hisopos.black_hole_won_caption": "{user} dominou o {type_label}: ganhou {points} pt e absorveu {lost_points} pt de {rivals} rival(is).",
        "hisopos.race_won_popup": "Você venceu a corrida! Ganhou {points} pt.",
        "hisopos.expired_caption_collected": "Era um {type_label}. Você perdeu! Não dá pontos, mas descobriu um cotonete vencido.",
        "hisopos.expired_caption_mystery": "O Misterioso era um {type_label}. Você perdeu! Não dá pontos nem um cotonete vencido.",
        "hisopos.expired_popup_collected": "Chegou tarde: sem pontos, mas colecionou um cotonete vencido.",
        "hisopos.expired_popup_mystery": "Chegou tarde. O Misterioso revelou o tipo, mas não dá pontos nem um Vencido.",
    },
    "pt_PT": {
        "hisopos.type.frenetic": "cotonete frenético",
        "hisopos.type.black_hole": "cotonete buraco negro",
        "hisopos.type.expired": "cotonete expirado",
        "hisopos.appeared_race": "Apareceu um {type_label}!\nA primeira pessoa a chegar a {target} toques vence.",
        "hisopos.race_button": "Premir",
        "hisopos.race_press_popup": "O teu toque contou: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Esse toque foi demasiado rápido e não contou.",
        "hisopos.race_won_caption": "{user} venceu a corrida pelo {type_label} e ganhou {points} pt.",
        "hisopos.black_hole_won_solo_caption": "{user} dominou sozinho o {type_label} e ganhou {points} pt.",
        "hisopos.black_hole_won_caption": "{user} dominou o {type_label}: ganhou {points} pt e absorveu {lost_points} pt de {rivals} rival(is).",
        "hisopos.race_won_popup": "Venceste a corrida! Ganhaste {points} pt.",
        "hisopos.expired_caption_collected": "Era um {type_label}. Perdeste-o! Não dá pontos, mas descobriste um cotonete expirado.",
        "hisopos.expired_caption_mystery": "O Misterioso era um {type_label}. Perdeste-o! Não dá pontos nem um cotonete expirado.",
        "hisopos.expired_popup_collected": "Chegaste tarde: sem pontos, mas colecionaste um cotonete expirado.",
        "hisopos.expired_popup_mystery": "Chegaste tarde. O Misterioso revelou o tipo, mas não dá pontos nem um Expirado.",
    },
    "quz": {
        "hisopos.type.frenetic": "phaway hisopo",
        "hisopos.type.black_hole": "yana uchku hisopo",
        "hisopos.type.expired": "pacha tukusqa hisopo",
        "hisopos.appeared_race": "Huk {type_label} rikurimun!\n{target} ñit'iyta ñawpaq chayaqmi atipan.",
        "hisopos.race_button": "Ñit'iy",
        "hisopos.race_press_popup": "Ñit'isqayki yupakun: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Ancha utqay ñit'inki, mana yupakunchu.",
        "hisopos.race_won_caption": "{user} {type_label} rayku kallpayta atiparqun, {points} puntutataq hap'in.",
        "hisopos.black_hole_won_solo_caption": "{user} sapallan {type_label}ta atipan, {points} puntutataq hap'in.",
        "hisopos.black_hole_won_caption": "{user} {type_label}ta atipan: {points} puntuta hap'in, {lost_points} puntutaq {rivals} masinkunamanta suq'un.",
        "hisopos.race_won_popup": "Kallpayta atipanki! {points} puntuta hap'inki.",
        "hisopos.expired_caption_collected": "{type_label} karqan. Chinkachirqanki! Mana puntuyuqchu, ichaqa pacha tukusqa hisopota huñunki.",
        "hisopos.expired_caption_mystery": "Pakaqa {type_label} karqan. Chinkachirqanki! Mana puntuyuqchu nitaq pacha tukusqapas.",
        "hisopos.expired_popup_collected": "Unayña: mana puntuyuqchu, ichaqa pacha tukusqa hisopota huñunki.",
        "hisopos.expired_popup_mystery": "Unayña. Pakaqa ima kasqanta rikuchin, mana puntuta nitaq pacha tukusqata qunchu.",
    },
    "ru": {
        "hisopos.type.frenetic": "Неистовая палочка",
        "hisopos.type.black_hole": "Палочка — чёрная дыра",
        "hisopos.type.expired": "Просроченная палочка",
        "hisopos.appeared_race": "Появилась {type_label}!\nПобедит тот, кто первым нажмёт {target} раз.",
        "hisopos.race_button": "Нажать",
        "hisopos.race_press_popup": "Нажатие засчитано: {current}/{target}.",
        "hisopos.race_too_fast_popup": "Нажатие было слишком быстрым и не засчитано.",
        "hisopos.race_won_caption": "{user} выиграл гонку за {type_label} и получил {points} очков.",
        "hisopos.black_hole_won_solo_caption": "{user} в одиночку покорил {type_label} и получил {points} очков.",
        "hisopos.black_hole_won_caption": "{user} покорил {type_label}: получил {points} очков и поглотил {lost_points} очков у {rivals} соперника(ов).",
        "hisopos.race_won_popup": "Вы выиграли гонку! Получено {points} очков.",
        "hisopos.expired_caption_collected": "Это была {type_label}. Вы опоздали! Очков нет, но Просроченная добавлена в коллекцию.",
        "hisopos.expired_caption_mystery": "Таинственная была типом «{type_label}». Вы опоздали! Очков и Просроченной нет.",
        "hisopos.expired_popup_collected": "Слишком поздно: очков нет, но Просроченная добавлена в коллекцию.",
        "hisopos.expired_popup_mystery": "Слишком поздно. Таинственная раскрылась, но не даёт очков или Просроченную.",
    },
    "zh_Hans": {
        "hisopos.type.frenetic": "狂热棉签",
        "hisopos.type.black_hole": "黑洞棉签",
        "hisopos.type.expired": "过期棉签",
        "hisopos.appeared_race": "{type_label}出现了！\n最先按到{target}次的人获胜。",
        "hisopos.race_button": "按下",
        "hisopos.race_press_popup": "本次有效：{current}/{target}。",
        "hisopos.race_too_fast_popup": "按得太快，本次不计数。",
        "hisopos.race_won_caption": "{user}赢得{type_label}竞赛，获得{points}分。",
        "hisopos.black_hole_won_solo_caption": "{user}独自征服{type_label}，获得{points}分。",
        "hisopos.black_hole_won_caption": "{user}征服{type_label}：获得{points}分，并吸收{lost_points}分，来自{rivals}名对手。",
        "hisopos.race_won_popup": "你赢了！获得{points}分。",
        "hisopos.expired_caption_collected": "原来是{type_label}。错过了！没有分数，但发现了一根过期棉签。",
        "hisopos.expired_caption_mystery": "神秘棉签原来是{type_label}。错过了！没有分数，也没有过期棉签。",
        "hisopos.expired_popup_collected": "来晚了：没有分数，但收藏了一根过期棉签。",
        "hisopos.expired_popup_mystery": "来晚了。神秘棉签揭晓类型，但不给分数或过期棉签。",
    },
    "zh_Hant": {
        "hisopos.type.frenetic": "狂熱棉花棒",
        "hisopos.type.black_hole": "黑洞棉花棒",
        "hisopos.type.expired": "過期棉花棒",
        "hisopos.appeared_race": "{type_label}出現了！\n最先按到{target}次的人獲勝。",
        "hisopos.race_button": "按下",
        "hisopos.race_press_popup": "本次有效：{current}/{target}。",
        "hisopos.race_too_fast_popup": "按得太快，本次不計數。",
        "hisopos.race_won_caption": "{user}贏得{type_label}競賽，獲得{points}分。",
        "hisopos.black_hole_won_solo_caption": "{user}獨自征服{type_label}，獲得{points}分。",
        "hisopos.black_hole_won_caption": "{user}征服{type_label}：獲得{points}分，並吸收{lost_points}分，來自{rivals}名對手。",
        "hisopos.race_won_popup": "你贏了！獲得{points}分。",
        "hisopos.expired_caption_collected": "原來是{type_label}。錯過了！沒有分數，但發現了一根過期棉花棒。",
        "hisopos.expired_caption_mystery": "神祕棉花棒原來是{type_label}。錯過了！沒有分數，也沒有過期棉花棒。",
        "hisopos.expired_popup_collected": "來晚了：沒有分數，但收藏了一根過期棉花棒。",
        "hisopos.expired_popup_mystery": "來晚了。神祕棉花棒揭曉類型，但不給分數或過期棉花棒。",
    },
}

HISOPO_BOMB_RULE_UPDATES: dict[str, tuple[str, str, str]] = {
    "es": ("Común: 46,65 %", "Común: 42,65 %", "- Bomba: 4 %, muestra 16 casillas. Hay una que la desactiva por +10 pt, una que explota por -10 pt y 14 neutras. Cada casilla se usa una vez; desactivar o explotar cierra el tablero. Solo una desactivación suma el Bomba a la colección y programa el día siguiente."),
    "en": ("Common: 46.65%", "Common: 42.65%", "- Bomb: 4%, shows 16 squares. One defuses it for +10 pt, one explodes for -10 pt, and 14 are neutral. Each square is used once; defusing or exploding closes the board. Only a defusal adds the Bomb to the collection and schedules the next day."),
    "es_ES": ("Común: 46,65 %", "Común: 42,65 %", "- Bomba: 4 %, muestra 16 casillas. Una la desactiva por +10 pt, una explota por -10 pt y 14 son neutras. Cada casilla se usa una vez; desactivar o explotar cierra el tablero. Solo una desactivación añade el Bomba a la colección y programa el día siguiente."),
    "ca": ("Comú: 46,65 %", "Comú: 42,65 %", "- Bomba: 4 %, mostra 16 caselles. Una la desactiva per +10 pt, una explota per -10 pt i 14 són neutres. Cada casella s'usa una vegada; desactivar o explotar tanca el tauler. Només desactivar-la afegeix la Bomba a la col·lecció i programa l'endemà."),
    "de": ("Gewöhnlich: 46,65 %", "Gewöhnlich: 42,65 %", "- Bombe: 4 %, zeigt 16 Felder. Eines entschärft für +10 Pkt., eines explodiert für -10 Pkt., 14 sind neutral. Jedes Feld gilt einmal; Entschärfung oder Explosion beendet das Brett. Nur die Entschärfung sammelt die Bombe und plant den nächsten Tag."),
    "eu": ("Arrunta: % 46,65", "Arrunta: % 42,65", "- Bonba: % 4, 16 lauki erakusten ditu. Batek +10 puntu emanez indargabetzen du, batek -10 punturekin lehertzen du eta 14 neutroak dira. Lauki bakoitza behin erabiltzen da; indargabetzeak edo leherketak taula ixten du. Indargabetzeak bakarrik gehitzen du bildumara eta biharamuna programatzen du."),
    "fr": ("Commun : 46,65 %", "Commun : 42,65 %", "- Bombe : 4 %, affiche 16 cases. Une la désamorce pour +10 pt, une explose pour -10 pt et 14 sont neutres. Chaque case ne sert qu'une fois ; désamorçage ou explosion ferme la grille. Seul le désamorçage l'ajoute à la collection et programme le lendemain."),
    "gn": ("Jepivegua: 46,65 %", "Jepivegua: 42,65 %", "- Mbokapu: 4 %, ohechauka 16 renda. Peteĩ ombogue ha ome'ẽ +10 kyta, peteĩ okapu ha oipe'a 10 kyta, ha 14 ndojapói mba'eve. Peteĩteĩ ojepuru peteĩ jevy; oñembogue térã okapúrõ oñemboty. Oñembogue ramo añoite oike ñembyatýpe ha oñemohenda ko'ẽrõ."),
    "it": ("Comune: 46,65 %", "Comune: 42,65 %", "- Bomba: 4 %, mostra 16 caselle. Una la disinnesca per +10 pt, una esplode per -10 pt e 14 sono neutre. Ogni casella vale una volta; disinnesco o esplosione chiudono il tabellone. Solo il disinnesco la aggiunge alla collezione e programma il giorno dopo."),
    "ja": ("通常：46.65%", "通常：42.65%", "- 爆弾：4%。16マスのうち1つは解除で+10点、1つは爆発で-10点、14個は何も起きません。各マスは1回限りで、解除か爆発で終了します。解除時のみコレクションに加わり、翌日を予約します。"),
    "la": ("Commune: 46,65 %", "Commune: 42,65 %", "- Pyrobolicum: 4 %, sedecim loca ostendit. Unum +10 punctis exarmat, unum -10 punctis displodit, quattuordecim neutra sunt. Quisque locus semel valet; exarmatio vel displosio tabulam claudit. Sola exarmatio collectioni addit et diem posterum ordinat."),
    "nl": ("Gewoon: 46,65%", "Gewoon: 42,65%", "- Bom: 4%, toont 16 vakken. Eén ontmantelt voor +10 pt, één ontploft voor -10 pt en 14 zijn neutraal. Elk vak geldt één keer; ontmanteling of explosie sluit het bord. Alleen ontmantelen voegt de Bom toe aan de collectie en plant de volgende dag."),
    "pt_BR": ("Comum: 46,65%", "Comum: 42,65%", "- Bomba: 4%, mostra 16 casas. Uma desarma por +10 pt, uma explode por -10 pt e 14 são neutras. Cada casa vale uma vez; desarmar ou explodir fecha o tabuleiro. Só desarmar adiciona a Bomba à coleção e agenda o dia seguinte."),
    "pt_PT": ("Comum: 46,65 %", "Comum: 42,65 %", "- Bomba: 4 %, mostra 16 casas. Uma desarma por +10 pt, uma explode por -10 pt e 14 são neutras. Cada casa vale uma vez; desarmar ou explodir fecha o tabuleiro. Só desarmar adiciona a Bomba à coleção e agenda o dia seguinte."),
    "quz": ("Sapsi: 46,65 %", "Sapsi: 42,65 %", "- Bomba: 4 %, 16 tawkuta rikuchin. Huknin wañuchispa +10 puntuta qun, huknin tuqyaspa -10 puntuta qun, 14 mana imatapas ruranchu. Sapa tawku huk kutilla; wañuchiy utaq tuqyay tabla wichq'an. Wañuchisqallam huñuyman yapakun hinaspa paqarinpaq wakichin."),
    "ru": ("Обычная: 46,65 %", "Обычная: 42,65 %", "- Бомба: 4 %, показывает 16 ячеек. Одна обезвреживает за +10 очков, одна взрывается за -10, а 14 нейтральны. Каждая ячейка используется один раз; обезвреживание или взрыв закрывают поле. Только обезвреживание добавляет Бомбу в коллекцию и планирует следующий день."),
    "zh_Hans": ("普通：46.65%", "普通：42.65%", "- 炸弹：4%，显示16格。一格拆弹得+10分，一格爆炸扣10分，其余14格无事发生。每格只能使用一次；拆弹或爆炸后棋盘关闭。只有拆弹成功才计入收藏并安排次日出现。"),
    "zh_Hant": ("普通：46.65%", "普通：42.65%", "- 炸彈：4%，顯示16格。一格拆彈得+10分，一格爆炸扣10分，其餘14格無事發生。每格只能使用一次；拆彈或爆炸後棋盤關閉。只有拆彈成功才計入收藏並安排次日出現。"),
}

HISOPO_RACE_RULE_UPDATES: dict[str, tuple[str, str, str]] = {
    "es": ("Común: 42,65 %", "Común: 34,65 %", "- Frenético: 4 %. Quien primero lleva su contador propio a 20 gana +3 pt.\n- Agujero negro: 4 % y carrera individual a 20. Si participa solo el ganador, suma +10 pt; con rivales, cada perdedor cede tantas unidades como pulsaciones hizo y el ganador recibe el menor valor entre 10 y el total cedido.\n- Vencido: el primer toque después del límite revela qué tipo era y no da puntos. Si no apareció como Misterioso, ese usuario colecciona un Vencido y la foto cambia a Vencido; si era Misterioso, revela la imagen real y no entrega Vencido."),
    "en": ("Common: 42.65%", "Common: 34.65%", "- Frenetic: 4%. The first person whose own counter reaches 20 presses earns +3 pt.\n- Black hole: 4% and an individual race to 20. A solo winner gets +10 pt; with rivals, every loser gives up one point per counted press and the winner receives the smaller of 10 or the total transferred.\n- Expired: the first late press reveals the original type and gives no points. A non-Mystery appearance gives that user one Expired collectible and changes to its image; a Mystery reveals the real image and gives no Expired collectible."),
    "es_ES": ("Común: 42,65 %", "Común: 34,65 %", "- Frenético: 4 %. La primera persona cuyo contador propio llega a 20 pulsaciones gana +3 pt.\n- Agujero negro: 4 % y carrera individual a 20. Si solo participa quien gana, suma +10 pt; con rivales, cada perdedor cede tantos puntos como pulsaciones hizo y quien gana recibe el menor valor entre 10 y el total cedido.\n- Caducado: la primera pulsación tras el límite revela qué tipo era y no da puntos. Si no apareció como Misterioso, ese usuario colecciona un Caducado y cambia su imagen; si era Misterioso, revela la imagen real y no entrega Caducado."),
    "ca": ("Comú: 42,65 %", "Comú: 34,65 %", "- Frenètic: 4 %. La primera persona amb un comptador propi que arriba a 20 pulsacions guanya +3 pt.\n- Forat negre: 4 % i cursa individual a 20. Si el guanyador participa sol, suma +10 pt; amb rivals, cada perdedor cedeix tants punts com pulsacions ha fet i el guanyador rep el menor entre 10 i el total cedit.\n- Caducat: la primera pulsació tardana revela el tipus i no dona punts. Si no apareixia com a Misteriós, l'usuari col·lecciona un Caducat i en mostra la imatge; si era Misteriós, mostra la imatge real i no dona Caducat."),
    "de": ("Gewöhnlich: 42,65 %", "Gewöhnlich: 34,65 %", "- Rasend: 4 %. Die erste Person, deren eigener Zähler 20 Klicks erreicht, erhält +3 Pkt.\n- Schwarzes Loch: 4 %, ein individuelles Rennen bis 20. Allein gibt es +10 Pkt.; mit Gegnern verliert jeder einen Punkt je eigenem Klick und der Sieger erhält höchstens 10 bzw. die kleinere übertragene Summe.\n- Abgelaufen: Der erste späte Klick enthüllt die Art, gibt aber keine Punkte. Außerhalb einer Mysteriösen Erscheinung sammelt die Person ein Abgelaufenes und dessen Bild erscheint; ein Mysteriöses enthüllt nur das echte Bild."),
    "eu": ("Arrunta: % 42,65", "Arrunta: % 34,65", "- Frenetikoa: % 4. Bere kontagailua 20 sakatzera iristen den lehenak +3 puntu irabazten ditu.\n- Zulo beltza: % 4 eta 20ra arteko banakako lasterketa. Bakarrik badago, irabazleak +10 puntu; arerioekin, galtzaile bakoitzak bere sakatze adina puntu galtzen ditu eta irabazleak 10 eta guztizko transferentziaren arteko txikiena hartzen du.\n- Iraungia: berandu egindako lehen sakatzeak benetako mota erakusten du, punturik gabe. Ez bazen Misteriotsu agertu, erabiltzaileak Iraungia biltzen du; Misteriotsuak benetako irudia bakarrik erakusten du."),
    "fr": ("Commun : 42,65 %", "Commun : 34,65 %", "- Frénétique : 4 %. La première personne dont le compteur individuel atteint 20 pressions gagne +3 pt.\n- Trou noir : 4 %, course individuelle à 20. Seul, le gagnant reçoit +10 pt ; avec des adversaires, chacun perd autant de points que ses pressions et le gagnant reçoit le minimum entre 10 et le total transféré.\n- Expiré : la première pression tardive révèle le type sans point. Hors Mystérieux, cette personne collectionne un Expiré et son image apparaît ; un Mystérieux révèle l'image réelle sans donner d'Expiré."),
    "gn": ("Jepivegua: 42,65 %", "Jepivegua: 34,65 %", "- Sarambi: 4 %. Pe puruhára ipapaha tee oguahẽva tenonde 20 jopyhápe ohupyty +3 kyta.\n- Kuára hũ: 4 % ha ñani peteĩteĩva 20 peve. Peteĩnte oñanírõ ohupyty +10; hetárõ, peteĩteĩ oguejy ojopy haguéicha ha oganáva ohupyty michĩvéva 10 térã kyta oñembohasáva apytépe.\n- Oñembyaíva: jopyha tenondegua ára rire ohechauka mba'eichagua kuri, kyta'ỹre. Ndaha'éirõ Ñemi, ojopyva ombyaty Oñembyaíva; Ñemi ohechauka ta'anga añetegua añoite."),
    "it": ("Comune: 42,65 %", "Comune: 34,65 %", "- Frenetico: 4 %. La prima persona il cui contatore individuale raggiunge 20 pressioni guadagna +3 pt.\n- Buco nero: 4 %, corsa individuale a 20. Da solo il vincitore prende +10 pt; con rivali, ognuno perde tanti punti quante pressioni e il vincitore riceve il minore fra 10 e il totale trasferito.\n- Scaduto: la prima pressione tardiva rivela il tipo senza punti. Fuori da un Misterioso, quella persona colleziona uno Scaduto e ne vede l'immagine; un Misterioso mostra l'immagine reale senza dare lo Scaduto."),
    "ja": ("通常：42.65%", "通常：34.65%", "- 熱狂：4%。自分のカウンターが最初に20回へ達した人が+3点を獲得します。\n- ブラックホール：4%、各自が20回を目指す競争です。単独なら+10点。対戦者がいれば各敗者は自分の押下数ぶん失い、勝者は10点と移動総数の小さい方を得ます。\n- 期限切れ：期限後の最初の押下で正体を表示し、得点はありません。ミステリー表示でなければ押した人が期限切れを収集して画像も変わります。ミステリーなら本当の画像だけを表示します。"),
    "la": ("Commune: 42,65 %", "Commune: 34,65 %", "- Freneticum: 4 %. Primus cuius numerus proprius ad 20 pressiones pervenit +3 puncta accipit.\n- Foramen atrum: 4 %, certamen singulorum ad 20. Solus victor +10 accipit; cum aemulis, quisque victus tot puncta quot pressiones amittit et victor minorem inter 10 et summam translatam accipit.\n- Expletum: prima pressio sera genus aperit sine punctis. Nisi Mysteriosum visum erat, homo Expletum colligit et imago mutatur; Mysteriosum imaginem veram aperit nec Expletum dat."),
    "nl": ("Gewoon: 42,65%", "Gewoon: 34,65%", "- Razend: 4%. De eerste persoon van wie de eigen teller 20 drukken bereikt, krijgt +3 pt.\n- Zwart gat: 4%, een individuele race tot 20. Alleen krijgt de winnaar +10 pt; met rivalen verliest ieder punten gelijk aan diens drukken en krijgt de winnaar de kleinste waarde van 10 of het overgedragen totaal.\n- Verlopen: de eerste late druk onthult het type zonder punten. Buiten een Mysterie verzamelt die gebruiker een Verlopen en verschijnt die afbeelding; een Mysterie toont alleen de echte afbeelding."),
    "pt_BR": ("Comum: 42,65%", "Comum: 34,65%", "- Frenético: 4%. A primeira pessoa cujo contador individual chega a 20 toques ganha +3 pt.\n- Buraco negro: 4%, corrida individual até 20. Sozinho, o vencedor ganha +10 pt; com rivais, cada perdedor cede pontos iguais aos próprios toques e o vencedor recebe o menor valor entre 10 e o total transferido.\n- Vencido: o primeiro toque atrasado revela o tipo sem dar pontos. Fora de um Misterioso, essa pessoa coleciona um Vencido e a imagem muda; um Misterioso só revela a imagem real."),
    "pt_PT": ("Comum: 42,65 %", "Comum: 34,65 %", "- Frenético: 4 %. A primeira pessoa cujo contador individual chega a 20 toques ganha +3 pt.\n- Buraco negro: 4 %, corrida individual até 20. Sozinho, o vencedor ganha +10 pt; com rivais, cada perdedor cede pontos iguais aos próprios toques e o vencedor recebe o menor valor entre 10 e o total transferido.\n- Expirado: o primeiro toque tardio revela o tipo sem dar pontos. Fora de um Misterioso, essa pessoa coleciona um Expirado e a imagem muda; um Misterioso só revela a imagem real."),
    "quz": ("Sapsi: 42,65 %", "Sapsi: 34,65 %", "- Phaway: 4 %. Kikin yupayninwan 20 ñit'iyta ñawpaq chayaqqa +3 puntuta hap'in.\n- Yana uchku: 4 %, sapakama 20 kama kallpay. Sapallan atipaq +10 puntuta hap'in; hukkunawanqa sapa mana atipaq ñit'isqan hina puntuta chinkachin, atipaqtaq 10 utaq llapan apachisqa ukhupi aswan huch'uyta hap'in.\n- Pacha tukusqa: qhipa ñawpaq ñit'iyqa imayna kasqanta rikuchin, mana puntuyuq. Mana Paka hina rikurirqan chayqa ñit'iq Pacha tukusqata huñun; Pakaqa chiqaq rikch'ayllata rikuchin."),
    "ru": ("Обычная: 42,65 %", "Обычная: 34,65 %", "- Неистовая: 4 %. Первый игрок, чей личный счётчик достигает 20 нажатий, получает +3 очка.\n- Чёрная дыра: 4 %, индивидуальная гонка до 20. Единственный участник получает +10; с соперниками каждый проигравший теряет очки по числу своих нажатий, победитель получает минимум из 10 и общей передачи.\n- Просроченная: первое позднее нажатие раскрывает вид без очков. Если это не была Таинственная оболочка, игрок собирает Просроченную и видит её картинку; Таинственная показывает настоящий вид без Просроченной."),
    "zh_Hans": ("普通：42.65%", "普通：34.65%", "- 狂热：4%。个人计数最先达到20次的人获得+3分。\n- 黑洞：4%，每人各自竞争达到20次。独自参赛得+10分；有对手时，每名败者按自己的有效次数失分，胜者获得10分与总转移分中的较小值。\n- 过期：超时后的首次按键会揭示原类型，但不得分。若外观不是神秘，按键者收藏一根过期棉签并更换图片；神秘只揭示真实图片，不给过期收藏。"),
    "zh_Hant": ("普通：42.65%", "普通：34.65%", "- 狂熱：4%。個人計數最先達到20次的人獲得+3分。\n- 黑洞：4%，每人各自競爭達到20次。獨自參賽得+10分；有對手時，每名敗者按自己的有效次數失分，勝者獲得10分與總轉移分中的較小值。\n- 過期：逾時後的首次按鍵會揭示原類型，但不得分。若外觀不是神祕，按鍵者收藏一根過期棉花棒並更換圖片；神祕只揭示真實圖片，不給過期收藏。"),
}

HISOPO_MYSTERY_GIANT_COLLECTION_NOTES: dict[str, str] = {
    "es": "Si oculta un Gigante, solo quien lo revela suma Misterioso; al completarlo, todos los participantes suman Gigante. En una carrera, quien revela suma Misterioso y quien gana suma el tipo real. Si vence oculto, no suma ninguno.",
    "en": "If it hides a Giant, only its revealer collects the Mystery; once completed, every participant collects the Giant. In a race, the revealer collects Mystery and the winner collects the real type. If it expires hidden, neither is collected.",
    "es_ES": "Si oculta un Gigante, solo quien lo revela suma Misterioso; al completarlo, todos los participantes suman Gigante. En una carrera, quien revela suma Misterioso y quien gana suma el tipo real. Si caduca oculto, no suma ninguno.",
    "ca": "Si amaga un Gegant, només qui el revela suma Misteriós; en completar-lo, tots els participants sumen Gegant. En una cursa, qui revela suma Misteriós i qui guanya suma el tipus real. Si caduca ocult, no en suma cap.",
    "de": "Verbirgt es einen Riesen, sammelt nur die enthüllende Person das Mysteriöse; nach Abschluss sammeln alle Beteiligten den Riesen. Im Rennen sammelt der Enthüller das Mysteriöse und der Sieger die echte Art. Verfällt es verborgen, zählt keines.",
    "eu": "Erraldoi bat ezkutatzen badu, agerian uzten duenak bakarrik biltzen du Misteriotsua; osatzean, parte-hartzaile guztiek Erraldoia biltzen dute. Lasterketan agerian uzten duenak Misteriotsua eta irabazleak benetako mota biltzen du. Ezkutuan iraungiz gero, bat ere ez.",
    "fr": "S'il cache un Géant, seule la personne qui le révèle collectionne le Mystérieux ; une fois terminé, tous collectionnent le Géant. Dans une course, la personne qui révèle prend le Mystérieux et le gagnant le vrai type. Expiré caché, aucun ne compte.",
    "gn": "Ñemi omokañýrõ Tuichaitéva, ohechaukáva añoite ombyaty Ñemi; oñemohu'ãvo, mayma oipytyvõva ombyaty Tuichaitéva. Ñaníme ohechaukáva ombyaty Ñemi ha oganáva añetegua. Oñembyaírõ kañyhápe, ndojepapái.",
    "it": "Se nasconde un Gigante, solo chi lo rivela colleziona il Misterioso; al completamento, tutti collezionano il Gigante. In una corsa chi rivela prende il Misterioso e chi vince il tipo reale. Se scade nascosto, nessuno dei due conta.",
    "ja": "巨大を隠していた場合、ミステリーは正体を明かした人だけ、完成した巨大は参加者全員が獲得します。競争では公開者がミステリー、勝者が本当の種類を獲得します。隠れたまま期限切れならどちらも獲得しません。",
    "la": "Si Gigantem celat, solus qui revelat Mysteriosum colligit; perfecto, omnes Gigantem colligunt. In certamine revelator Mysteriosum, victor genus verum colligit. Si celatum expletur, neutrum colligitur.",
    "nl": "Verbergt het een Reus, dan verzamelt alleen de onthuller het Mysterie; na voltooiing verzamelt iedereen de Reus. In een race krijgt de onthuller het Mysterie en de winnaar het echte type. Verloopt het verborgen, dan telt geen van beide.",
    "pt_BR": "Se esconder um Gigante, só quem revela coleciona o Misterioso; ao concluir, todos colecionam o Gigante. Numa corrida, quem revela leva o Misterioso e quem vence leva o tipo real. Se vencer oculto, nenhum conta.",
    "pt_PT": "Se esconder um Gigante, só quem revela coleciona o Misterioso; ao concluir, todos colecionam o Gigante. Numa corrida, quem revela recebe o Misterioso e quem vence o tipo real. Se expirar oculto, nenhum conta.",
    "quz": "Hatun hisopota pakaptinqa, rikurichiq sapallan Paka hisopota huñun; tukuchiptinku llapan yanapaqkuna Hatunta huñunku. Kallpaypi rikurichiq Paka hisopota, atipaqtaq chiqaq layata huñun. Pakasqa tukukuptinqa manam mayqinpas yupakunchu.",
    "ru": "Если внутри Гигантская, Таинственную получает только раскрывший, а завершённую Гигантскую — все участники. В гонке раскрывший получает Таинственную, победитель — настоящий вид. Если она истекла скрытой, не засчитывается ни одна.",
    "zh_Hans": "若其中是巨型棉签，只有揭晓者获得神秘，完成后所有参与者获得巨型。竞赛中揭晓者获得神秘，胜者获得真实类型；若隐藏状态下过期，两者都不计。",
    "zh_Hant": "若其中是巨型棉花棒，只有揭曉者獲得神祕，完成後所有參與者獲得巨型。競賽中揭曉者獲得神祕，勝者獲得真實類型；若隱藏狀態下過期，兩者都不計。",
}

for _language, _translations in HISOPO_SPECIAL_TRANSLATIONS.items():
    HISOPO_TRANSLATIONS[_language].update(_translations)
for _language, _translations in HISOPO_RULE_TRANSLATIONS.items():
    HISOPO_TRANSLATIONS[_language].update(_translations)
for _language, _translations in HISOPO_COOPERATIVE_TRANSLATIONS.items():
    HISOPO_TRANSLATIONS[_language].update(_translations)
for _language, _translations in HISOPO_COLLECTION_TRANSLATIONS.items():
    HISOPO_TRANSLATIONS[_language].update(_translations)
for _language, _translations in HISOPO_BOMB_TRANSLATIONS.items():
    HISOPO_TRANSLATIONS[_language].update(_translations)
for _language, _translations in HISOPO_RACE_TRANSLATIONS.items():
    HISOPO_TRANSLATIONS[_language].update(_translations)
for _language, (_old_common, _new_common, _extra_rules) in HISOPO_COOPERATIVE_RULE_UPDATES.items():
    _rules = HISOPO_TRANSLATIONS[_language]["hisopos.rules"]
    if _old_common not in _rules or "\n- /hisopos" not in _rules:  # pragma: no cover
        raise RuntimeError(f"No pude extender las reglas de Hisopos para {_language}.")
    HISOPO_TRANSLATIONS[_language]["hisopos.rules"] = _rules.replace(
        _old_common,
        _new_common,
        1,
    ).replace(
        "\n- /hisopos",
        f"\n{_extra_rules}\n- /hisopos",
        1,
    )
for _language, (_old_common, _new_common, _bomb_rule) in HISOPO_BOMB_RULE_UPDATES.items():
    _rules = HISOPO_TRANSLATIONS[_language]["hisopos.rules"]
    if _old_common not in _rules or "\n- /hisopos" not in _rules:  # pragma: no cover
        raise RuntimeError(f"No pude agregar las reglas del Hisopo bomba para {_language}.")
    HISOPO_TRANSLATIONS[_language]["hisopos.rules"] = _rules.replace(
        _old_common,
        _new_common,
        1,
    ).replace("\n- /hisopos", f"\n{_bomb_rule}\n- /hisopos", 1)
for _language, (_old_common, _new_common, _race_rules) in HISOPO_RACE_RULE_UPDATES.items():
    _rules = HISOPO_TRANSLATIONS[_language]["hisopos.rules"]
    if _old_common not in _rules or "\n- /hisopos" not in _rules:  # pragma: no cover
        raise RuntimeError(f"No pude agregar las reglas de carreras para {_language}.")
    HISOPO_TRANSLATIONS[_language]["hisopos.rules"] = _rules.replace(
        _old_common,
        _new_common,
        1,
    ).replace("\n- /hisopos", f"\n{_race_rules}\n- /hisopos", 1)
for _language, _count_rule in HISOPO_GIANT_COUNT_RULES.items():
    HISOPO_TRANSLATIONS[_language]["hisopos.rules"] = HISOPO_TRANSLATIONS[_language][
        "hisopos.rules"
    ].replace("\n- /hisopos", f"\n{_count_rule}\n- /hisopos", 1)
for _language, _schedule_rule in HISOPO_SCHEDULE_CAP_RULES.items():
    HISOPO_TRANSLATIONS[_language]["hisopos.rules"] = HISOPO_TRANSLATIONS[_language][
        "hisopos.rules"
    ].replace("\n- /hisopos", f"\n{_schedule_rule}\n- /hisopos", 1)
for _language, _collection_rule in HISOPO_COLLECTION_RULES.items():
    _collection_rule = _collection_rule.replace("12", "16", 1).replace(
        "duodecim", "sedecim", 1
    )
    _mystery_giant_note = HISOPO_MYSTERY_GIANT_COLLECTION_NOTES[_language]
    _collection_rule = f"{_collection_rule} {_mystery_giant_note}"
    HISOPO_COLLECTION_RULES[_language] = _collection_rule
    HISOPO_TRANSLATIONS[_language]["hisopos.rules"] = HISOPO_TRANSLATIONS[_language][
        "hisopos.rules"
    ].replace(
        "\n- /hisopos",
        f"\n{_collection_rule}\n- /hisopos",
        1,
    )


_HISOPO_RULE_HEADINGS: dict[str, tuple[str, str, str, str, str]] = {
    "es": ("Cómo jugar", "Tipos y probabilidades", "Juegos especiales", "Importante", "Comandos"),
    "en": ("How to play", "Types and probabilities", "Special games", "Important", "Commands"),
    "es_ES": ("Cómo jugar", "Tipos y probabilidades", "Juegos especiales", "Importante", "Comandos"),
    "ca": ("Com es juga", "Tipus i probabilitats", "Jocs especials", "Important", "Ordres"),
    "de": ("So wird gespielt", "Typen und Wahrscheinlichkeiten", "Spezialspiele", "Wichtig", "Befehle"),
    "eu": ("Nola jokatu", "Motak eta probabilitateak", "Joko bereziak", "Garrantzitsua", "Komandoak"),
    "fr": ("Comment jouer", "Types et probabilités", "Jeux spéciaux", "Important", "Commandes"),
    "gn": ("Mba'éichapa oñeñembosarái", "Mba'eichagua ha ikatuha", "Ñembosarái ambuéva", "Iñimportánteva", "Ñe'ẽmondo"),
    "it": ("Come si gioca", "Tipi e probabilità", "Giochi speciali", "Importante", "Comandi"),
    "ja": ("遊び方", "種類と確率", "特別ゲーム", "重要", "コマンド"),
    "la": ("Quomodo ludatur", "Genera et probabilitates", "Ludi speciales", "Notandum", "Praecepta"),
    "nl": ("Zo speel je", "Typen en kansen", "Speciale spellen", "Belangrijk", "Opdrachten"),
    "pt_BR": ("Como jogar", "Tipos e probabilidades", "Jogos especiais", "Importante", "Comandos"),
    "pt_PT": ("Como jogar", "Tipos e probabilidades", "Jogos especiais", "Importante", "Comandos"),
    "quz": ("Imayna pukllana", "Layakuna hinallataq rikurimunankuna", "Sapaq pukllaykuna", "Yuyarinapaq", "Kamachikuna"),
    "ru": ("Как играть", "Виды и вероятности", "Особые игры", "Важно", "Команды"),
    "zh_Hans": ("玩法", "类型与概率", "特殊玩法", "重要", "命令"),
    "zh_Hant": ("玩法", "類型與機率", "特殊玩法", "重要", "指令"),
}
_RULE_SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？])|(?<=[.!?])\s+")
_RULE_COMMANDS = ("/coleccionhisopos", "/reglashisopo", "/hisopos", "/config")


def _rule_text_html(text: str) -> str:
    rendered = escape(text)
    for command in _RULE_COMMANDS:
        rendered = rendered.replace(command, f"<code>{command}</code>")
    return rendered


def _first_rule_sentences(line: str, count: int) -> str:
    text = line.removeprefix("- ")
    sentences = [part for part in _RULE_SENTENCE_BOUNDARY.split(text) if part]
    return " ".join(sentences[:count])


def _rule_bullet_html(text: str, *, bold_label: bool = False) -> str:
    text = text.removeprefix("- ")
    if bold_label:
        for separator in (":", "："):
            label, found, detail = text.partition(separator)
            if found:
                return f"• <b>{escape(label + separator)}</b>{_rule_text_html(detail)}"
    return f"• {_rule_text_html(text)}"


def _compact_hisopo_rules(rules: str, headings: tuple[str, str, str, str, str]) -> str:
    lines = rules.splitlines()
    if len(lines) != 26:  # pragma: no cover - guards the localized rules template
        raise RuntimeError("El formato base de las reglas de Hisopos cambió.")
    how_to_play, types, special_games, important, commands = headings
    rendered = [
        f"<b>🧪 {escape(lines[0])}</b>",
        "",
        f"<b>🎮 {escape(how_to_play)}</b>",
        _rule_bullet_html(lines[2]),
        _rule_bullet_html(_first_rule_sentences(lines[3], 1)),
        "",
        f"<b>🎲 {escape(types)}</b>",
        *(_rule_bullet_html(line, bold_label=True) for line in lines[4:14]),
        "",
        f"<b>✨ {escape(special_games)}</b>",
        _rule_bullet_html(lines[16], bold_label=True),
        _rule_bullet_html(lines[17], bold_label=True),
        _rule_bullet_html(_first_rule_sentences(lines[18], 2), bold_label=True),
        _rule_bullet_html(_first_rule_sentences(lines[19], 2), bold_label=True),
        _rule_bullet_html(lines[20], bold_label=True),
        "",
        f"<b>ℹ️ {escape(important)}</b>",
        _rule_bullet_html(lines[14]),
        _rule_bullet_html(lines[21], bold_label=True),
        _rule_bullet_html(lines[22]),
        _rule_bullet_html(lines[23], bold_label=True),
        _rule_bullet_html(lines[24], bold_label=True),
        "",
        f"<b>⌨️ {escape(commands)}</b>",
        "• <code>/hisopos</code> · <code>/coleccionhisopos</code> · <code>/config</code>",
    ]
    return "\n".join(rendered)


for _language, _headings in _HISOPO_RULE_HEADINGS.items():
    HISOPO_TRANSLATIONS[_language]["hisopos.rules"] = _compact_hisopo_rules(
        HISOPO_TRANSLATIONS[_language]["hisopos.rules"],
        _headings,
    )
