"""Two languages (English, German) for the console and the kids `Robot`. Pure logic.

    >>> t("de", "i_see", color=color_word("green", "de"))
    'Ich sehe: gruen'
    >>> normalize("Licht ROT")
    'licht rot'

Messages live in one small table per language (no gettext). German **input** may use
umlauts (`normalize` turns them into ae/oe/ue/ss); German **output** is ASCII-only
(Windows code pages), so it is written with ae/oe/ue/ss.
"""

from __future__ import annotations

import os

EN = "en"
DE = "de"
LANGS = (EN, DE)

# Code points, not literals: printed/source strings stay ASCII (tests/test_portability.py).
_UMLAUTS = {0xE4: "ae", 0xF6: "oe", 0xFC: "ue", 0xDF: "ss"}  # ä ö ü ß


def normalize(text: str) -> str:
    """Lower case, umlauts spelled out (u-umlaut -> "ue", sharp s -> "ss")."""
    return text.lower().translate(_UMLAUTS)


def lang_from_word(word: str) -> str | None:
    """ "deutsch" / "german" / "de" -> "de", "english" / "englisch" / "en" -> "en"."""
    word = normalize(word.strip())
    if word in ("de", "deutsch", "german", "ger"):
        return DE
    if word in ("en", "english", "englisch", "eng"):
        return EN
    return None


def default_lang() -> str:
    """Language from BOOST_LANG (shell or .env, e.g. "de"), else English."""
    from lego_boost.config import load_env

    load_env()
    value = os.environ.get("BOOST_LANG", "")
    return lang_from_word(value.split("_")[0].split(".")[0]) or EN


# German colour words -> the English names in `kid.COLORS`. The first word per colour
# is the one shown in output.
COLORS_DE = {
    "aus": "off",
    "schwarz": "black",
    "rosa": "pink",
    "lila": "purple",
    "blau": "blue",
    "hellblau": "lightblue",
    "tuerkis": "cyan",
    "gruen": "green",
    "gelb": "yellow",
    "orange": "orange",
    "rot": "red",
    "weiss": "white",
    "pink": "pink",
    "violett": "purple",
}
_COLOR_SHOWN_DE = {english: german for german, english in reversed(COLORS_DE.items())}


def color_to_english(word: str, english_colors) -> str | None:
    """An English or German colour word -> its English name, or None."""
    word = normalize(word)
    if word in english_colors:
        return word
    return COLORS_DE.get(word)


def color_word(english: str, lang: str) -> str:
    """How to show a colour (an English name from `kid`, or "nothing") in `lang`."""
    if lang != DE:
        return english
    if english == "nothing":
        return "nichts"
    return _COLOR_SHOWN_DE.get(english, english)


def color_words(lang: str, english_colors) -> list[str]:
    """Colour words for completion and help in `lang`."""
    if lang == DE:
        return list(dict.fromkeys(_COLOR_SHOWN_DE[c] for c in english_colors))
    return list(english_colors)


TILT_DE = {
    "up": "oben",
    "down": "unten",
    "left": "links",
    "right": "rechts",
    "front": "vorne",
    "back": "hinten",
}


def tilt_word(tilt: str, lang: str) -> str:
    """How to show a tilt state from `Robot.tilt()` in `lang`."""
    return TILT_DE.get(tilt, tilt) if lang == DE else tilt


PARAM_NAMES_DE = {
    "seconds": "Sekunden",
    "degrees": "Grad",
    "color": "Farbe",
    "port": "Anschluss",
    "speed": "Tempo",
    "command": "Befehl",
    "language": "Sprache",
}

MESSAGES = {
    EN: {
        # parser
        "hint": " Did you mean '{guess}'?",
        "unknown_word": "I don't know '{word}'.{hint} Type 'help' to see all commands.",
        "which_way": "Say which way: 'turn left 90' or 'turn right 90'",
        "raw_only": "'{name}' only works in raw mode. Type 'raw' to switch.",
        "no_values": "'{name}' takes no values, e.g. '{example}'",
        "at_most": "'{name}' takes at most {most} value(s), e.g. '{example}'",
        "needs": "'{name}' needs a {param}, e.g. '{example}'",
        "not_number": "{where} must be a number, e.g. '{example}'",
        "not_zero": "{where} must not be 0",
        "between": "{where} must be between {low:g} and {high:g}",
        "unknown_color": "I don't know the color '{color}'.{hint} Colors: {colors}",
        "bad_port": "{where} must be one of {ports}",
        "no_help": "No help for '{name}'. Type 'help' to see all commands.",
        "help_example": "  example: {example}",
        "help_also": "  also: {words}",
        "help_raw_only": "  (raw mode only)",
        "help_title": "Commands:",
        "help_raw_title": "Raw commands:",
        "help_tip": "Tip: a color name alone works too, e.g. 'blue'. Deutsch: 'sprache deutsch'.",
        # session
        "stopped": "Stopped.",
        "i_see": "I see: {color}",
        "nothing_in_front": "Nothing in front of me.",
        "distance": "Distance: {distance}",
        "battery": "Battery: {volts:.2f} V",
        "battery_unknown": "Battery: unknown",
        "sensors": "color={color} distance={distance} battery={volts} V",
        "hub_devices": "Hub devices:",
        "no_devices": "No device list available.",
        "mode_raw": "Raw mode. Type 'help' to see the commands.",
        "mode_simple": "Simple mode. Type 'help' to see the commands.",
        "not_connected": "The robot is not connected. Type 'reconnect' (press the green "
        "button) or 'exit'.",
        "hub_stuck": "The hub stopped answering.",
        "hub_lost": "Lost the hub.",
        "press_reconnect": "{why} Press the green button, then type 'reconnect' (or 'exit').",
        "connecting": "Connecting ... press the green button on the hub.",
        "could_not_connect": "Could not connect: {error}",
        "connected_again": "Connected again!",
        "oops": "Oops, '{name}' did not work: {error}",
        "language_now": "Language: English. ('sprache deutsch' switches to German.)",
        "language_unknown": "I only know 'english' and 'deutsch'.",
        # console
        "banner": "LEGO BOOST console. Type 'help' for commands, 'exit' to stop.",
        "status": " {state} | mode: {mode} | battery: {battery} | last color: {color} ",
        "ctrl_c": "Ctrl+C - stopping.",
        "connected": "connected",
        "disconnected": "disconnected",
        "closed": "closed",
        "not open": "not open",
        "simple": "simple",
        "raw": "raw",
        "prompt": "robot",
        # tui
        "tui_forward": "^ Forward",
        "tui_back": "v Back",
        "tui_left": "<- Left",
        "tui_right": "Right ->",
        "tui_stop": "STOP",
        "tui_ask_color": "What color?",
        "tui_ask_distance": "How far?",
        "tui_placeholder": "Type a command (help) - arrow keys drive, space stops",
        "tui_sensors": "Sensors",
        "tui_color": "Color",
        "tui_distance": "Distance",
        "tui_tilt": "Tilt",
        "tui_battery": "Battery",
        "tui_keys": "Arrows: drive   Space/Esc: STOP   F1: help   Ctrl+Q: quit",
        "tui_banner": "Ready! Click the buttons, use the arrow keys, or type 'help'.",
        # robot (kid.py, sim.py)
        "robot_connected": "Robot connected!",
        "robot_connected_sim": "Robot connected! (simulated - no hub needed)",
        "robot_bye": "Robot stopped. Bye!",
        "robot_unknown_color": "I don't know the color '{color}'. Try one of: {colors}",
        "no_extra_motor": "No extra motor plugged into port C or D.",
        "bad_trim": "BOOST_TRIM={value} is not a number from -{max} to {max}. Using {used}.",
        "no_sensor": "No color/distance sensor plugged in.",
    },
    DE: {
        "hint": " Meinst du '{guess}'?",
        "unknown_word": "'{word}' kenne ich nicht.{hint} Tippe 'hilfe' fuer alle Befehle.",
        "which_way": "Sag wohin: 'dreh links 90' oder 'dreh rechts 90'",
        "raw_only": "'{name}' geht nur im Roh-Modus. Tippe 'roh' zum Umschalten.",
        "no_values": "'{name}' braucht keine Zahl, z.B. '{example}'",
        "at_most": "'{name}' nimmt hoechstens {most} Wert(e), z.B. '{example}'",
        "needs": "'{name}' braucht: {param}, z.B. '{example}'",
        "not_number": "{where} muss eine Zahl sein, z.B. '{example}'",
        "not_zero": "{where} darf nicht 0 sein",
        "between": "{where} muss zwischen {low:g} und {high:g} liegen",
        "unknown_color": "Die Farbe '{color}' kenne ich nicht.{hint} Farben: {colors}",
        "bad_port": "{where} muss einer von {ports} sein",
        "no_help": "Keine Hilfe fuer '{name}'. Tippe 'hilfe' fuer alle Befehle.",
        "help_example": "  Beispiel: {example}",
        "help_also": "  auch: {words}",
        "help_raw_title": "Roh-Befehle:",
        "help_raw_only": "  (nur im Roh-Modus)",
        "help_title": "Befehle:",
        "help_tip": "Tipp: ein Farbname allein geht auch, z.B. 'blau'. "
        "English: 'language english'.",
        "stopped": "Angehalten.",
        "i_see": "Ich sehe: {color}",
        "nothing_in_front": "Vor mir ist nichts.",
        "distance": "Abstand: {distance}",
        "battery": "Batterie: {volts:.2f} V",
        "battery_unknown": "Batterie: unbekannt",
        "sensors": "Farbe={color} Abstand={distance} Batterie={volts} V",
        "hub_devices": "Geraete am Hub:",
        "no_devices": "Keine Geraeteliste da.",
        "mode_raw": "Roh-Modus. Tippe 'hilfe' fuer die Befehle.",
        "mode_simple": "Einfacher Modus. Tippe 'hilfe' fuer die Befehle.",
        "not_connected": "Der Roboter ist nicht verbunden. Tippe 'verbinden' (gruenen Knopf "
        "druecken) oder 'ende'.",
        "hub_stuck": "Der Hub antwortet nicht mehr.",
        "hub_lost": "Der Hub ist weg.",
        "press_reconnect": "{why} Druecke den gruenen Knopf und tippe 'verbinden' (oder 'ende').",
        "connecting": "Verbinde ... druecke den gruenen Knopf am Hub.",
        "could_not_connect": "Keine Verbindung: {error}",
        "connected_again": "Wieder verbunden!",
        "oops": "Hoppla, '{name}' hat nicht geklappt: {error}",
        "language_now": "Sprache: Deutsch. ('language english' schaltet auf Englisch.)",
        "language_unknown": "Ich kenne nur 'deutsch' und 'english'.",
        "banner": "LEGO BOOST Konsole. Tippe 'hilfe' fuer Befehle, 'ende' zum Aufhoeren.",
        "status": " {state} | Modus: {mode} | Batterie: {battery} | letzte Farbe: {color} ",
        "ctrl_c": "Strg+C - ich halte an.",
        "connected": "verbunden",
        "disconnected": "getrennt",
        "closed": "beendet",
        "not open": "nicht offen",
        "simple": "einfach",
        "raw": "roh",
        "prompt": "roboter",
        "tui_forward": "^ Vor",
        "tui_back": "v Zurueck",
        "tui_left": "<- Links",
        "tui_right": "Rechts ->",
        "tui_stop": "STOPP",
        "tui_ask_color": "Welche Farbe?",
        "tui_ask_distance": "Wie weit?",
        "tui_placeholder": "Befehl tippen (hilfe) - Pfeiltasten fahren, Leertaste haelt an",
        "tui_sensors": "Sensoren",
        "tui_color": "Farbe",
        "tui_distance": "Abstand",
        "tui_tilt": "Neigung",
        "tui_battery": "Batterie",
        "tui_keys": "Pfeile: fahren   Leertaste/Esc: STOPP   F1: Hilfe   Strg+Q: Ende",
        "tui_banner": "Los geht's! Klick die Knoepfe, nimm die Pfeiltasten oder tippe 'hilfe'.",
        "robot_connected": "Roboter verbunden!",
        "robot_connected_sim": "Roboter verbunden! (nur simuliert - kein Hub noetig)",
        "robot_bye": "Roboter angehalten. Tschuess!",
        "robot_unknown_color": "Die Farbe '{color}' kenne ich nicht. Probier: {colors}",
        "no_extra_motor": "Kein extra Motor an Anschluss C oder D.",
        "bad_trim": "BOOST_TRIM={value} ist keine Zahl von -{max} bis {max}. Nehme {used}.",
        "no_sensor": "Kein Farb-/Abstandssensor eingesteckt.",
    },
}


def t(lang: str, key: str, **values) -> str:
    """The message `key` in `lang` (falls back to English), filled with `values`."""
    table = MESSAGES.get(lang, MESSAGES[EN])
    return table.get(key, MESSAGES[EN][key]).format(**values)
