from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.plc_simulator import PLCSimulator

from enum import Enum, auto
from src.plc_io_definitions import DigitalInputs, AnalogInputs, DigitalOutputs

class Steps(Enum):
    """
    Enum class to define the States of the system.
    Improves readability and scalability of the code.
    """
    # Normal operation states
    STOP = auto() # Default state
    PREFILLING = auto()
    INITIALISED = auto()
    FILLING = auto()
    HEATING = auto()
    DISCHARGING_VALVE = auto()

    # Error states
    ERROR_A0 = auto() # Tank Level Too High Alarm 
    ERROR_A1 = auto() # Tank Level Too Low Alarm 
    ERROR_A2 = auto() # Fluid Temperature Too High Alarm 
    ERROR_A3 = auto() # Fluid Temperature Too Low Alarm 
    ERROR_A4 = auto() # Discharging Door Open Alarm 
    ERROR_A5 = auto() # Emergency Button Pressed Alarm 

class Transitions:
    """
    This class exists only to improve readability of the code.
    Without this I got lost a bit.
    """
    def __init__(self, plc: "PLCSimulator"):
        self.plc = plc

    def start_button_pressed_and_gate_closed(self) -> bool:
        return (self.plc.digital_inputs[DigitalInputs.START_BUTTON]
                and self.plc.digital_inputs[DigitalInputs.DISCHARG_GT_CLOSED])

    def tank_reached_low_level(self) -> bool:
        return self.plc.digital_inputs[DigitalInputs.L_LVL_SENSOR]

    def run_button_pressed(self) -> bool:
        return self.plc.digital_inputs[DigitalInputs.RUN_BUTTON]

    def tank_reached_high_level(self) -> bool:
        return self.plc.digital_inputs[DigitalInputs.H_LVL_SENSOR]

    def temperature_reached_setpoint(self) -> bool:
        return (self.plc.analog_inputs[AnalogInputs.TEMPERATURE_SENSOR]
                >= self.plc.DESIRED_TEMPERATURE)

    def tank_back_to_low_level(self) -> bool:
        return self.plc.digital_inputs[DigitalInputs.L_LVL_SENSOR]

    def stop_requested(self) -> bool:
        return self.plc.digital_inputs[DigitalInputs.STOP_BUTTON]

class PLCCommonOperations:
    """
    This class contains common operations that are used in the PLC.
    It encapsulates the logic.
    """
    def __init__(self, plc: "PLCSimulator"):
        self.plc = plc

    def stop_system(self):
        """
        Stop the system, but do not trigger errors.
        """
        self.plc.digital_outputs[DigitalOutputs.FILLING_VALVE_OPEN] = False
        self.plc.digital_outputs[DigitalOutputs.HEATING_ON] = False
        self.plc.digital_outputs[DigitalOutputs.DISCHARGING_VALVE_OPEN] = False

    def stop_heating_open_gate(self):
        """
        Stop heating and open the discharging gate.
        """
        self.plc.digital_outputs[DigitalOutputs.HEATING_ON] = False
        self.plc.digital_outputs[DigitalOutputs.DISCHARGING_GATE_OPEN] = True
        
    def stop_fluid_flow_open_gate(self):
        """
        Stop fluid flow and open the discharging gate.
        """
        self.plc.digital_outputs[DigitalOutputs.FILLING_VALVE_OPEN] = False
        self.plc.digital_outputs[DigitalOutputs.DISCHARGING_GATE_OPEN] = True