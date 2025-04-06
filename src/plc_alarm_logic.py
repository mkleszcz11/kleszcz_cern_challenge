from enum import Enum, auto

class Alarms(Enum):
    TANK_TOO_HIGH = "A0"
    TANK_TOO_LOW = "A1"
    TEMP_TOO_HIGH = "A2"
    TEMP_TOO_LOW = "A3"
    DOOR_OPEN = "A4"
    ES_PRESSED = "A5"