from __future__ import annotations


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
            "- Si nadie captura un Hisopo, se pudre y no le quita puntos a nadie. Los normales vencen a los 20 minutos y el Fugaz directo al minuto. Los puntajes pueden quedar negativos.\n"
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
            "- If nobody captures a Swab, it rots without taking points from anyone. Regular ones expire after 20 minutes and a direct Fleeting one after a minute. Scores may be negative.\n"
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
            "- Si nadie captura un hisopo, se pudre sin quitar puntos a nadie. Los normales caducan a los 20 minutos y el Fugaz directo al minuto. La puntuación puede ser negativa.\n"
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
            "- Si ningú captura un bastonet, es podreix sense restar punts a ningú. Els normals caduquen als 20 minuts i el Fugaç directe al minut. La puntuació pot ser negativa.\n"
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
            "- Wird keines gefangen, verrottet es ohne Punktabzug. Normale verfallen nach 20 Minuten, direkte Flüchtige nach einer Minute. Punktestände dürfen negativ sein.\n"
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
            "- Inork harrapatzen ez badu, usteldu egiten da inori punturik kendu gabe. Arruntak 20 minutuan eta Iheskor zuzena minutu batean iraungitzen dira. Puntuazioa negatiboa izan daiteke.\n"
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
            "- Si personne ne le capture, il pourrit sans retirer de points. Les normaux expirent après 20 minutes et le Fugace direct après une minute. Les scores peuvent être négatifs.\n"
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
            "- Avave ndojapyhýiramo, oñembyai oipe'a'ỹre kyta avavégui. Jepivegua opa 20 minútope ha Pya'e tee peteĩ minútope. Ikatu oĩ kyta vai.\n"
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
            "- Se nessuno lo cattura, marcisce senza sottrarre punti. I normali scadono dopo 20 minuti e il Fugace diretto dopo un minuto. I punteggi possono essere negativi.\n"
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
            "- 誰も捕獲しなければ誰の点も減らさず腐ります。通常は20分、直接出た一瞬は1分で期限切れです。得点は負になることがあります。\n"
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
            "- Si nemo capit, putrescit nec cuiquam puncta aufert. Communia post 20 minuta, Fugax directum post minutum pereunt. Puncta negativa esse possunt.\n"
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
            "- Als niemand het vangt, rot het zonder punten af te trekken. Gewone verlopen na 20 minuten en directe Vluchtige na één minuut. Scores mogen negatief zijn.\n"
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
            "- Se ninguém capturar, ele apodrece sem tirar pontos de ninguém. Os normais expiram em 20 minutos e o Fugaz direto em um minuto. A pontuação pode ficar negativa.\n"
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
            "- Se ninguém o capturar, apodrece sem retirar pontos. Os normais expiram em 20 minutos e o Fugaz direto num minuto. A pontuação pode ser negativa.\n"
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
            "- Mana pipas hap'iptinqa ismukun, manataq pipas puntuta chinkachinchu. Sapsikuna 20 minutupi, Utqay chiqaptaq huk minutupi tukukun. Yupayqa mana allinmanpas chayayta atin.\n"
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
            "- Если никто не поймал палочку, она сгниёт, никого не штрафуя. Обычные живут 20 минут, прямая Мимолётная — минуту. Счёт может быть отрицательным.\n"
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
            "- 若无人捕获，棉签会腐烂，不扣任何人的分。普通棉签20分钟失效，直接出现的瞬逝棉签一分钟失效。分数可以为负。\n"
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
            "- 若無人捕獲，棉花棒會腐爛，不扣任何人的分。普通棉花棒20分鐘失效，直接出現的瞬逝棉花棒一分鐘失效。分數可以為負。\n"
            "- 每次有效捕獲都會安排次日出現，但假棉花棒和超過一分鐘的隱藏瞬逝棉花棒除外。\n"
            "- /hisopos 顯示本群排行榜。"
        ),
    },
}

for _language, _translations in HISOPO_SPECIAL_TRANSLATIONS.items():
    HISOPO_TRANSLATIONS[_language].update(_translations)
for _language, _translations in HISOPO_RULE_TRANSLATIONS.items():
    HISOPO_TRANSLATIONS[_language].update(_translations)
