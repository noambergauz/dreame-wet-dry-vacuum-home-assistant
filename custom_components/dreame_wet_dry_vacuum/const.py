"""Constants for Dreame wet & dry vacuum integration."""

DOMAIN = "dreame_wet_dry_vacuum"
MANUFACTURER = "Dreame"
MODEL = "H14 Pro"

# API — one shard per region: https://{region}.iot.dreame.tech:13267
# Verified resolvable 2026-09: eu, cn, us, sg, ru, kr.
# There is NO dedicated il/me shard (DNS NXDOMAIN); Israeli accounts live on
# one of the shards below — usually sg (Singapore serves TR/Middle-East, cf.
# Tasshack/dreame-vacuum) — so try sg first, then us/eu.
EU_BASE_URL = "https://eu.iot.dreame.tech:13267"
CN_BASE_URL = "https://cn.iot.dreame.tech:13267"
US_BASE_URL = "https://us.iot.dreame.tech:13267"
SG_BASE_URL = "https://sg.iot.dreame.tech:13267"
RU_BASE_URL = "https://ru.iot.dreame.tech:13267"
KR_BASE_URL = "https://kr.iot.dreame.tech:13267"

# DREAME_BASIC_AUTH = base64("dreame_appv1:AP^dv@z@SQYVxN88") — app client credentials
DREAME_BASIC_AUTH = "Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
DREAME_TENANT_ID = "000000"
DREAME_PASSWORD_SALT = "RAylYC%fmSKp7%Tq"
DREAME_RLC_KEY = b"EETjszu*XI5znHsI"
DREAME_IOT_PREFIX = "10000"

ENDPOINTS = {
    "token": "/dreame-auth/oauth/token",
    "device_list": "/dreame-user-iot/iotuserbind/device/listV2",
    "send_command": "/dreame-iot-com-{prefix}/device/sendCommand",
    # Reads the cloud-cached property values by key ("siid.piid"). Works on this
    # model where the realtime get_properties RPC returns null. Verified live.
    "status_props": "/dreame-user-iot/iotstatus/props",
}

# Device status codes for the H14 Pro (model dreame.hold.w2306e).
# Source: official Dreame keyDefine file, property 2.1 (English labels).
# This mirrors the `latestStatus` field returned by device/listV2.
DEVICE_STATUS = {
    1: "Washing",
    2: "Offline",
    3: "Idle",
    4: "Charging",
    5: "Self-cleaning",
    6: "Drying",
    7: "Standby",
    8: "Vacuuming",
    9: "Filling clean water",
    10: "Mopping paused",
    11: "Self-cleaning paused",
    12: "Drying paused",
    13: "OTA upgrading",
    14: "Voice software upgrading",
    15: "Charge complete",
    # 16-22: "Washing" in the official dictionary, but each code actually
    # maps to a distinct cleaning MODE (confirmed by the user).
    16: "Washing — Auto mode",
    17: "Washing — Ultra mode",
    18: "Washing — Vacuum mode",
    19: "Washing",
    20: "Washing",
    21: "Washing",
    22: "Washing",
    23: "Drying",
    24: "Drying",
    25: "Drying",
    26: "Self-cleaning",
    27: "Self-cleaning",
    28: "Self-cleaning",
    29: "Spot mode paused",
}

# Status enum names decoded from the official app plugin (index.android.bundle):
# StandBy:3 Charging:4 SelfCleaning:5 SelfDrying:6 Sleeping:7 Convenient:8
# AddWater:9 WashingPause:10 CleaningPause:11 DryingPause:12 OTAUpgrading:13
# ... SelfDrying_Quite:25 SelfCleaning_Fast:26 SelfCleaning_Deep:27
# SelfCleaning_Smart:28 ConvenientPause:29

# Coarse activity grouping (useful for automations / binary states)
STATUS_GROUP = {
    1: "mopping", 16: "mopping", 17: "mopping", 18: "mopping",
    19: "mopping", 20: "mopping", 21: "mopping", 22: "mopping",
    8: "vacuuming",
    3: "idle", 7: "idle",
    4: "charging", 15: "charging",
    5: "self_cleaning", 11: "self_cleaning", 26: "self_cleaning",
    27: "self_cleaning", 28: "self_cleaning",
    6: "drying", 12: "drying", 23: "drying", 24: "drying", 25: "drying",
    9: "filling_water",
    10: "paused", 29: "paused",
    13: "updating", 14: "updating",
    2: "offline",
}

# Property siid/piid known for this model
PROP_STATUS = (2, 1)  # device status (matches latestStatus)

# Known MQTT properties for the H14 Pro, discovered by live capture.
# (siid, piid): (key, label_fr, unit_or_None, is_status_enum)
# Confidence: HIGH for status/battery/progress; the rest are exposed raw.
# Meta schema per property:
#   key, name, icon, unit, device_class ("battery"|"duration"|"timestamp")
#   enum=True            -> map int via DEVICE_STATUS
#   list_scalar=True     -> value arrives as a list; use first element
#   timestamp=True       -> value is a Unix epoch (seconds)
#   diagnostic=True      -> entity category Diagnostic
# Noms issus de la spec officielle du plugin app (index.android.bundle).
# Le mapping SIID/PIID nommé par Dreame fait autorité ; voir debug/dumps/DECODED_SPEC.md.
# NB : "name" est documentaire ; l'affichage passe par translation_key = "key"
# (section "entity" de translations/en.json et fr.json).
KNOWN_MQTT_PROPS: dict[tuple[int, int], dict] = {
    # --- Service principal (SIID 1) ---
    (2, 1): {"key": "status", "name": "Status", "enum": True, "icon": "mdi:robot-vacuum-variant"},
    (3, 1): {"key": "battery", "name": "Battery", "unit": "%", "device_class": "battery"},
    (1, 28): {"key": "work_mode", "name": "Work mode", "icon": "mdi:state-machine", "diagnostic": True},
    (1, 29): {"key": "level_washing", "name": "Washing level", "icon": "mdi:water-percent", "state_class": "measurement"},
    (1, 30): {"key": "level_drying", "name": "Drying level", "icon": "mdi:hair-dryer", "state_class": "measurement"},
    (1, 53): {"key": "total_time", "name": "Total runtime", "unit": "s", "device_class": "duration", "icon": "mdi:timer-cog", "diagnostic": True},
    (1, 54): {"key": "total_clean_count", "name": "Total clean count", "icon": "mdi:counter", "state_class": "total_increasing"},
    (1, 55): {"key": "start_time", "name": "Start time", "device_class": "timestamp", "timestamp": True, "icon": "mdi:clock-start", "diagnostic": True},
    (1, 56): {"key": "total_time_self_dry", "name": "Total self-dry time", "unit": "s", "device_class": "duration", "icon": "mdi:timer-sand", "diagnostic": True},
    (1, 57): {"key": "total_time_self_clean", "name": "Total self-clean time", "unit": "s", "device_class": "duration", "icon": "mdi:timer-sand", "diagnostic": True},
    # Champs lus via l'API cleanLog (hors modèle Prop du plugin) — mapping empirique conservé
    (1, 47): {"key": "last_clean_time", "name": "Last clean time", "device_class": "timestamp", "timestamp": True, "icon": "mdi:clock-check"},
    (1, 64): {"key": "last_clean_duration", "name": "Last clean duration", "unit": "s", "device_class": "duration", "icon": "mdi:timer"},
    (1, 49): {"key": "clean_count_2", "name": "Clean counter (alt.)", "icon": "mdi:counter", "state_class": "total_increasing", "diagnostic": True},
    (1, 68): {"key": "last_vacuum_duration", "name": "Last vacuum duration", "unit": "s", "device_class": "duration", "diagnostic": True},
    (1, 69): {"key": "last_mop_duration", "name": "Last mop duration", "unit": "s", "device_class": "duration", "diagnostic": True},
    # --- Consommables : "vie restante" = MINUTES restantes (raw, diagnostic).
    #     Les heures/% sont exposés par des capteurs dédiés (CONSUMABLE_SENSORS).
    #     Les props "max" (x.6/x.2) ne sont jamais publiées par le cloud → non mappées.
    (6, 7): {"key": "front_brush_left", "name": "Front roller brush — minutes left", "unit": "min", "icon": "mdi:rotate-right", "diagnostic": True},
    (7, 7): {"key": "back_brush_left", "name": "Back roller brush — minutes left", "unit": "min", "icon": "mdi:rotate-right", "diagnostic": True},
    (19, 3): {"key": "filter_left", "name": "Filter — minutes left", "unit": "min", "icon": "mdi:air-filter", "diagnostic": True},
    # Never reported to date (dust bag, suction brush/filter) — kept raw just in case.
    (20, 3): {"key": "dustbag_left", "name": "Dust bag — minutes left", "unit": "min", "icon": "mdi:sack", "diagnostic": True},
    (21, 7): {"key": "suck_brush_left", "name": "Suction brush — minutes left", "unit": "min", "icon": "mdi:rotate-right", "diagnostic": True},
    (22, 7): {"key": "suck_filter_left", "name": "Suction filter — minutes left", "unit": "min", "icon": "mdi:air-filter", "diagnostic": True},
    # --- Settings mirrored in read (also exposed as controls, see below) ---
    (16, 3): {"key": "elec_water", "name": "Electrolysis / detergent", "icon": "mdi:flash", "diagnostic": True},
    (1, 67): {"key": "detergent_fav", "name": "Detergent preference", "icon": "mdi:bottle-tonic-plus", "diagnostic": True},
    # --- Alerts / faults (SIID 4, plugin names: warn/error/warnPush) ---
    (4, 1): {"key": "warn", "name": "Warnings", "icon": "mdi:alert", "bitmask": True, "decode": "warn", "diagnostic": True},
    (4, 2): {"key": "error", "name": "Error codes", "icon": "mdi:alert-circle", "bitmask": True, "decode": "error", "diagnostic": True},
    (4, 3): {"key": "warn_push", "name": "Push notification (raw)", "icon": "mdi:bell-alert", "bitmask": True, "diagnostic": True},
    # --- Niveau d'eau / aspiration : non modélisés par le plugin sous SIID 4,
    #     mapping empirique conservé (vu en capture live) ---
    (4, 5): {"key": "water_level_set", "name": "Water level (setting)", "unit": "%", "list_scalar": True, "icon": "mdi:water-percent"},
    (4, 6): {"key": "water_level", "name": "Water level", "unit": "%", "icon": "mdi:water"},
    (4, 7): {"key": "suction_mode", "name": "Suction mode", "list_scalar": True, "icon": "mdi:fan"},
}

# Capteurs de consommables.
# La valeur "left" (x.7 / x.3) est en MINUTES restantes → heures = left / 60
# (aucune constante nécessaire). Le % a besoin d'une vie totale : on lit la prop
# "max" si l'appareil la publie un jour (mise en cache), sinon on retombe sur
# `full_life_min` (réf. documentée de l'app : filtre & rouleaux = 60 h = 3600 min).
# État principal = heures restantes ; % + minutes en attributs.
CONSUMABLE_SENSORS: list[dict] = [
    {"key": "front_brush", "name": "Front roller brush", "left": "6.7", "max": "6.6",
     "full_life_min": 3600, "icon": "mdi:rotate-right"},
    {"key": "back_brush", "name": "Back roller brush", "left": "7.7", "max": "7.6",
     "full_life_min": 3600, "icon": "mdi:rotate-right"},
    {"key": "filter", "name": "Filter", "left": "19.3", "max": "19.2",
     "full_life_min": 3600, "icon": "mdi:air-filter"},
]

# Clés "max" à interroger malgré tout : si l'appareil finit par les publier, le %
# bascule automatiquement sur la vraie capacité au lieu du repli `full_life_min`.
CONSUMABLE_MAX_KEYS: list[str] = [c["max"] for c in CONSUMABLE_SENSORS]

# ---------------------------------------------------------------------------
# Décodage des champs warn (4.1) / error (4.2).
# Reproduit decodeWarnV2/decodeErrorV2 du plugin de l'app : décalage cumulatif
# puis masque. Chaque champ = (pos, cal_mask, {valeur_du_champ: libellé_FR}).
# Les positions sont relatives (cumul des `pos` dans l'ordre). Voir DECODED_SPEC.md.
# ---------------------------------------------------------------------------
WARN_DECODE: list[tuple[int, int, dict[int, str]]] = [
    (0, 1, {1: "Clean water tank empty"}),
    (1, 1, {1: "Detergent empty"}),
    (1, 3, {1: "Dirty brush/tube — run self-cleaning",
            2: "Dirty brush/tube — run self-cleaning",
            3: "Dirty brush/tube — run self-cleaning"}),
    (2, 1, {}), (1, 1, {}), (1, 1, {}), (1, 1, {}),
    (1, 1, {1: "Dirty water tank needs cleaning (after self-cleaning)"}),  # bit 8
    (1, 1, {}), (1, 1, {}), (1, 1, {}), (1, 1, {}), (1, 1, {}), (1, 1, {}), (1, 1, {}),
    (1, 1, {1: "Station water shortage"}),   # bit 16
    (1, 1, {1: "Station filter needs replacement"}),  # bit 17
]
ERROR_DECODE: list[tuple[int, int, dict[int, str]]] = [
    (0, 15, {}),
    (4, 63, {1: "Roller brush not installed",
             3: "Roller brush stuck — needs cleaning"}),  # bits 4-9
    (6, 1, {}),
    (1, 1, {1: "Dirty water tank not installed"}),   # bit 11
    (1, 1, {1: "Dirty water tank full — needs emptying"}),  # bit 12
    (1, 7, {}), (3, 15, {}), (4, 1, {}), (1, 1, {}), (1, 1, {}), (1, 1, {}),
    (1, 1, {1: "Device tube clogged"}),   # bit 24
    (1, 1, {}),
    (1, 1, {1: "Station tube clogged"}),   # bit 26
    (1, 1, {}),
    (1, 1, {1: "Dirty water tank clogged"}),  # bit 28
]


def decode_field_alerts(value: int, table: list[tuple[int, int, dict[int, str]]]) -> list[str]:
    """Decode a warn/error bitfield value into the list of active labels."""
    alerts: list[str] = []
    v = value
    for pos, cal, labels in table:
        if pos:
            v >>= pos
        field = v & cal
        if field in labels:
            alerts.append(labels[field])
    return alerts


# Capteurs binaires d'alerte spécifiques : valeur (data_key) & bit_mask.
# Permet plusieurs capteurs sur une même propriété (ex. plusieurs bits de 4.2).
ALERT_BINARY_SENSORS: list[dict] = [
    {"key": "dirty_tank_full", "name": "Dirty water tank full", "data_key": "4.2",
     "bit_mask": 4096, "device_class": "problem", "icon": "mdi:cup-water"},
    {"key": "dirty_tank_not_clean", "name": "Dirty water tank needs cleaning", "data_key": "4.1",
     "bit_mask": 256, "device_class": "problem", "icon": "mdi:cup-water"},
    {"key": "dirty_tank_missing", "name": "Dirty water tank missing", "data_key": "4.2",
     "bit_mask": 2048, "device_class": "problem", "icon": "mdi:cup-off-outline"},
    {"key": "clean_water_empty", "name": "Clean water tank empty", "data_key": "4.1",
     "bit_mask": 1, "device_class": "problem", "icon": "mdi:water-alert"},
    {"key": "detergent_empty", "name": "Detergent empty", "data_key": "4.1",
     "bit_mask": 2, "device_class": "problem", "icon": "mdi:bottle-tonic-outline"},
    {"key": "needs_self_clean", "name": "Self-cleaning recommended (dirty brush/tube)", "data_key": "4.1",
     "bit_mask": 12, "device_class": "problem", "icon": "mdi:broom"},
]

# Binary properties: (siid, piid): meta.
#   bit_mask=N  -> on when (value & N) != 0 (instead of value != 0)
KNOWN_BINARY_PROPS: dict[tuple[int, int], dict] = {
    # Confirmé par test isolé : 17.8 = ajout auto de détergent (1=activé, 0=désactivé)
    (17, 8): {"key": "auto_detergent_17", "name": "Auto detergent (sensor)", "icon": "mdi:bottle-tonic-plus", "diagnostic": True},
}

# ---------------------------------------------------------------------------
# Contrôles écrivables (set_properties). Découverts dans le plugin de l'app.
# Chaque entrée : (siid, piid): {key, name, icon, ...}
# ---------------------------------------------------------------------------

# Interrupteurs booléens (0/1).
#   optimistic=True -> l'état courant n'est PAS lisible (ni MQTT ni web) ; l'entité
#   reflète la dernière commande envoyée (assumed_state).
KNOWN_SWITCH_PROPS: dict[tuple[int, int], dict] = {
    (1, 3): {"key": "light_control", "name": "Light", "icon": "mdi:lightbulb", "optimistic": True},
    (1, 4): {"key": "auto_mix_detergent", "name": "Auto detergent mixing", "icon": "mdi:bottle-tonic-plus", "optimistic": True},
    (1, 7): {"key": "auto_backwash", "name": "Auto rinse", "icon": "mdi:water-sync"},
    (1, 9): {"key": "auto_dry_switch", "name": "Auto drying", "icon": "mdi:hair-dryer", "optimistic": True},
    (1, 11): {"key": "time_dry_after_clean", "name": "Timed dry after cleaning", "icon": "mdi:timer-cog", "optimistic": True},
    (16, 6): {"key": "custom_switch", "name": "Custom mode", "icon": "mdi:tune-variant"},
}

# Curseurs numériques : {min, max, step, unit} (+ optimistic si état non lisible)
KNOWN_NUMBER_PROPS: dict[tuple[int, int], dict] = {
    (1, 14): {"key": "volume", "name": "Voice volume", "icon": "mdi:volume-high", "min": 0, "max": 100, "step": 1, "unit": "%", "optimistic": True},
    (1, 12): {"key": "time_dry_value", "name": "Timed dry duration", "icon": "mdi:timer-sand", "min": 0, "max": 21600, "step": 600, "unit": "s", "optimistic": True},
    # Réglages du mode personnalisé (plages à confirmer ; valeurs entières observées 0-2)
    # 16.1/16.2 sont lisibles (web) ; 16.4 ne l'est pas → optimiste.
    # config=True : paramètres de réglage, pas des contrôles principaux.
    (16, 1): {"key": "clean_power", "name": "Suction power (custom)", "icon": "mdi:fan", "min": 0, "max": 3, "step": 1, "config": True},
    (16, 2): {"key": "clean_water", "name": "Water flow (custom)", "icon": "mdi:water", "min": 0, "max": 3, "step": 1, "config": True},
    (16, 4): {"key": "brush_speed", "name": "Brush speed (custom)", "icon": "mdi:rotate-right", "min": 0, "max": 3, "step": 1, "optimistic": True, "config": True},
}

# Listes déroulantes : {options: {int_value: option_key}}
# option_key is the stable (English) identifier; display text comes from
# translations/{en,fr}.json -> entity.select.<key>.state.<option_key>.
KNOWN_SELECT_PROPS: dict[tuple[int, int], dict] = {
    (23, 1): {
        "key": "power_wheel",
        "name": "Traction force",
        "icon": "mdi:car-traction-control",
        "options": {0: "light", 1: "balanced", 2: "strong"},
        "optimistic": True,
    },
}

# Boutons (envoient une valeur fixe ; commandes ponctuelles)
KNOWN_BUTTON_PROPS: dict[tuple[int, int], dict] = {
    (1, 1): {"key": "start_self_clean", "name": "Start self-cleaning", "icon": "mdi:water-sync", "press_value": 1},
    (1, 2): {"key": "start_self_dry", "name": "Start self-drying", "icon": "mdi:hair-dryer", "press_value": 1},
}

# Propriétés pilotées UNIQUEMENT par le push MQTT temps réel : le poll web (toutes
# les 5 min) lirait une valeur trop grossière/périmée et ferait "sauter" la valeur.
# Progression de lavage (1.29) et de séchage (1.30) changent toutes les ~36 s.
MQTT_ONLY_KEYS: set[tuple[int, int]] = {(1, 29), (1, 30)}

CONF_REGION = "region"
CONF_DEVICE_ID = "device_id"

REGIONS = {
    "eu": "Europe",
    "cn": "China / Asia",
    "us": "United States",
    "sg": "Singapore / Asia-Pacific (use for Israel / Middle East)",
    "ru": "Russia",
    "kr": "South Korea",
}
