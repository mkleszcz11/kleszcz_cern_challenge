from enum import Enum, auto

class DigitalInputs(Enum):
    """
    Enum class to map the Digital Inputs of the system to the PLC Inputs.
    In a real system, the inputs/outputs would be assigned
    to specific ports/pins and this implementation might save a lot
    of troubles. In case of this challenge it just improves readability
    (subjective).
    """
    # Digital inputs
    START_BUTTON = "DI0"       # Start button
    RUN_BUTTON = "DI1"         # Run button
    STOP_BUTTON = "DI2"        # Stop button
    ES_BUTTON = "DI3"          # Emergency button
    RST_BUTTON = "DI4"         # Reset button
    LL_LVL_SENSOR = "DI5"      # Low low level sensor
    L_LVL_SENSOR = "DI6"       # Low level sensor
    H_LVL_SENSOR = "DI7"       # High level sensor
    HH_LVL_SENSOR = "DI8"      # High high alarm
    DISCHARG_GT_CLOSED = "DI9" # Discharging gate closed

class AnalogInputs(Enum):
    """
    Enum class to map the Analog Inputs of the system to the PLC Inputs.
    """
    TEMPERATURE_SENSOR = "AI0" # Temperature sensor
 
class DigitalOutputs(Enum):
    """
    Enum class to map the Digital Inputs of the system to the PLC Outputs.
    """
    # Digital outputs
    FILLING_VALVE_OPEN = "DQ0"     # Filling valve
    DISCHARGING_VALVE_OPEN = "DQ1" # Discharging valve
    HEATING_ON = "DQ2"             # Heating element
    DISCHARGING_GATE_OPEN = "DQ3"  # Discharging gate
