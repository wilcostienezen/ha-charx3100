"""Constants for the CHARX 3100 integration."""

from __future__ import annotations

DOMAIN = "charx3100"

CONF_UNIT_ID = "unit_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MAX_CURRENT_LIMIT = "max_current_limit"
CONF_RESTORE_ON_RESET = "restore_on_reset"

DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
DEFAULT_SCAN_INTERVAL = 15  # seconds
DEFAULT_MAX_CURRENT_LIMIT = 32  # A
DEFAULT_RESTORE_ON_RESET = True

MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

# Controller registers (absolute)
REG_CHARGING_POINT_COUNT = 114

# Charging point registers: absolute address = point_number * 1000 + offset
CP_STRIDE = 1000
MAX_CHARGING_POINTS = 12

# One block read covers the status (x232-x299) and control (x300-x308) area.
BLOCK_START = 232
BLOCK_END = 308
BLOCK_LENGTH = BLOCK_END - BLOCK_START + 1  # 77 registers, well below the 125 limit

OFF_VOLTAGE_L1 = 232  # 2 words, mV
OFF_VOLTAGE_L2 = 234
OFF_VOLTAGE_L3 = 236
OFF_CURRENT_L1 = 238  # 2 words, mA (signed, -1 = not available)
OFF_CURRENT_L2 = 240
OFF_CURRENT_L3 = 242
OFF_ACTIVE_POWER = 244  # 2 words, mW
OFF_REACTIVE_POWER = 246  # 2 words, mvar (signed)
OFF_APPARENT_POWER = 248  # 2 words, mVA
OFF_ENERGY_TOTAL = 250  # 4 words, Wh
OFF_CONNECTION_TIME = 285  # 2 words, s
OFF_CHARGING_TIME = 287  # 2 words, s
OFF_ENERGY_SESSION = 289  # 4 words, Wh
OFF_ERROR_CODE = 293  # 2 words, bit field
OFF_DIGITAL_INPUTS = 295
OFF_PWM_DUTY_CYCLE = 296  # %
OFF_PWM_CURRENT = 297  # A
OFF_CABLE_CAPACITY = 298  # A
OFF_IEC_STATUS = 299  # 1 word ASCII, e.g. "C2"
OFF_CHARGING_RELEASE = 300  # 0/1, writable in release mode "Modbus"
OFF_MAX_CURRENT = 301  # A, 6-80
OFF_WATCHDOG_TIMER = 307  # s, 65535 = disabled

MIN_CURRENT = 6
ABSOLUTE_MAX_CURRENT = 80

# IEC 61851-1 state letter -> charging state option
CHARGING_STATES = {
    "A": "not_connected",
    "B": "connected",
    "C": "charging",
    "D": "charging_ventilation",
    "E": "error",
    "F": "not_available",
}
