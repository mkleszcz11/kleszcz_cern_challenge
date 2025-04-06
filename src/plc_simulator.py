
from asyncua import Server, ua
import asyncio

from src.plc_io_definitions import DigitalInputs, AnalogInputs, DigitalOutputs
from src.plc_utils import Steps, Transitions, PLCCommonOperations
from src.plc_alarm_logic import Alarms

class PLCSimulator:
    def __init__(self):
        # Constants, moved from the execute_control_logic method to make it more readable
        self.CYCLE_TIME = 0.2 # Time interval for cyclic execution (in seconds)
        self.DESIRED_TEMPERATURE = 45.0
        self.MAX_TEMPERATURE = 80.0
        self.MIN_TEMPERATURE = 10.0

        # Initialize input/output and alarm registers. Complete the registers with the needed signals
        self.digital_inputs = {
            DigitalInputs.START_BUTTON: False, # Start button, True when pressed, False otherwise
            DigitalInputs.RUN_BUTTON: False, # Run button, True when pressed, False otherwise
            DigitalInputs.STOP_BUTTON: False, # Stop button, True when pressed, False otherwise
            DigitalInputs.ES_BUTTON: False, # Emergency button, True when pressed, False otherwise
            DigitalInputs.RST_BUTTON: False, # Reset button, True when pressed, False otherwise
            DigitalInputs.LL_LVL_SENSOR: False, # Low low level sensor, True when water detected, False otherwise
            DigitalInputs.L_LVL_SENSOR: False, # Low level sensor, True when water detected, False otherwise
            DigitalInputs.H_LVL_SENSOR: False, # High level sensor, True when water detected, False otherwise
            DigitalInputs.HH_LVL_SENSOR: False, # High high level sensor, True when water detected, False otherwise
            DigitalInputs.DISCHARG_GT_CLOSED: True  # Tank discharging gate sensor. True when closed, False otherwise
            }

        self.analog_inputs = {
            AnalogInputs.TEMPERATURE_SENSOR: 20.0, # Temperature sensor, [Celsius]
            }

        self.digital_outputs = {
            DigitalOutputs.FILLING_VALVE_OPEN: False, # Filling system. True when on, False otherwise
            DigitalOutputs.DISCHARGING_VALVE_OPEN: False, # Tank discharging valve (normal operation). True when open, False otherwise
            DigitalOutputs.HEATING_ON: False, # Heating system. True when on, False otherwise
            DigitalOutputs.DISCHARGING_GATE_OPEN: True   # Tank discharging gate (complete discharging). True when closed, False otherwise.
            }

        # Alarms have Active, UnAck ("Unacknowledged"), and Status attributes
        #   Active: True if the alarm is active, False otherwise
        #   UnAck: True if the alarm is unacknowledged after it was triggered
        #   Status: True if the alarm is either active or unacknowledged
        self.alarms = {
            Alarms.TANK_TOO_HIGH: {"Active": False, "UnAck": False, "Status": False}, # Tank Level Too High Alarm
            Alarms.TANK_TOO_LOW:  {"Active": False, "UnAck": False, "Status": False}, # Tank Level Too Low Alarm
            Alarms.TEMP_TOO_HIGH: {"Active": False, "UnAck": False, "Status": False}, # Fluid Temperature Too High Alarm
            Alarms.TEMP_TOO_LOW:  {"Active": False, "UnAck": False, "Status": False}, # Fluid Temperature Too Low Alarm
            Alarms.DOOR_OPEN:     {"Active": False, "UnAck": False, "Status": False}, # Discharging Door Open Alarm
            Alarms.ES_PRESSED:    {"Active": False, "UnAck": False, "Status": False}  # Emergency Button Pressed Alarm
        }

        # Map alarms to steps. This is used to set the step when an alarm is triggered.
        self.map_alarm_to_step = {
            Alarms.TANK_TOO_HIGH: Steps.ERROR_A0,
            Alarms.TANK_TOO_LOW:  Steps.ERROR_A1,
            Alarms.TEMP_TOO_HIGH: Steps.ERROR_A2,
            Alarms.TEMP_TOO_LOW:  Steps.ERROR_A3,
            Alarms.DOOR_OPEN:     Steps.ERROR_A4,
            Alarms.ES_PRESSED:    Steps.ERROR_A5
        }

        # Alarms should be ordered by priority. The first one is the most important.
        # List is subjective, for more information please refer to README.md file.
        self.alarms_priority_order = (
            Alarms.ES_PRESSED,    # Emergency button pressed
            Alarms.TANK_TOO_HIGH, # Tank level too high
            Alarms.TEMP_TOO_HIGH, # Fluid temperature too high
            Alarms.TANK_TOO_LOW,  # Tank level too low
            Alarms.TEMP_TOO_LOW,  # Fluid temperature too low
            Alarms.DOOR_OPEN,     # Discharging door open
        )

        self.step = Steps.STOP # Start with system stopped, as indicated in the original code
        self.last_low_low_sensor_state = False # Helper variable to detect falling edge of low level sensor

        self.transitions = Transitions(self) # Initialize transitions object.
        self.common_operations_handler = PLCCommonOperations(self) # Initialize common operations object.
        self.trip = False # Error mode when True, normal operation when False 

    async def update_inputs(self):
        # Update digital input readings from the OPC UA server
        # Name is the enum, value must be taken to get the string value
        for name in self.digital_inputs.keys():
            myvar = await self.myobj.get_child(f"{self.idx}:{name.value}")
            value = await myvar.read_value()
            self.digital_inputs[name] = value

        # Update the analog input readings from the OPC UA server
        for name in self.analog_inputs.keys():
            myvar = await self.myobj.get_child(f"{self.idx}:{name.value}")
            value = await myvar.read_value()
            self.analog_inputs[name] = value

    async def write_outputs(self):
        # Complete the necessary code to write the output values into the OPC UA server
        # Enum again
        for name, value in self.digital_outputs.items():
            myvar = await self.myobj.get_child(f"{self.idx}:{name.value}")
            await myvar.write_value(value)

    async def update_alarms_active_state(self):
        #TODO: maybe it would be better to keep the active state untill the alarm is acknowledged, not rely only on the status
        #TODO: Read all alarms at once, instead of one by one
        # Tank level too high, high high level sensor active
        self.alarms[Alarms.TANK_TOO_HIGH]["Active"] = (
            self.digital_inputs[DigitalInputs.HH_LVL_SENSOR]  
        )
        # Falling edge on low low level sensor
        self.alarms[Alarms.TANK_TOO_LOW]["Active"] = (
            self.last_low_low_sensor_state
            and not self.digital_inputs[DigitalInputs.LL_LVL_SENSOR]
        )
        # Fluid temperature too high
        self.alarms[Alarms.TEMP_TOO_HIGH]["Active"] = (
            self.analog_inputs[AnalogInputs.TEMPERATURE_SENSOR] > self.MAX_TEMPERATURE
        )
        # Fluid temperature too low
        self.alarms[Alarms.TEMP_TOO_LOW]["Active"] = (
            self.analog_inputs[AnalogInputs.TEMPERATURE_SENSOR] < self.MIN_TEMPERATURE
        )
        # Discharging door open
        self.alarms[Alarms.DOOR_OPEN]["Active"] = (
            not self.digital_inputs[DigitalInputs.DISCHARG_GT_CLOSED]
        )
        # Emergency button pressed
        self.alarms[Alarms.ES_PRESSED]["Active"] = (
            self.digital_inputs[DigitalInputs.ES_BUTTON]
        )

        self.last_low_low_sensor_state = self.digital_inputs[DigitalInputs.LL_LVL_SENSOR]

    async def reset_alarms(self):
        # Reset all alarms to inactive and acknowledged
        for key in self.alarms.keys():
            self.alarms[key].update({"UnAck":False})
            self.alarms[key].update({"Status":False})

    async def set_alarms(self):
        """
        If the alarm is active, set UnAck and Status to True.
        Set the values to the OPC UA server.
        """
        for key, values in self.alarms.items():
            myalarm = await self.myobj.get_child(f"{self.idx}:{key.value}")
            # If the alarm is active, set UnAck and Status to True
            if values["Active"]:
                values["UnAck"] = True
                values["Status"] = True
            # Write the values to the OPC UA server
            for newkey, value in values.items():
                myvar = await myalarm.get_child(f"{self.idx}:{newkey}")
                await myvar.write_value(value)

    async def check_alarms_and_return_most_urgent(self):
        """
        Check the alarms and return the most urgent one.
        """
        for alarm_id in self.alarms_priority_order:
            alarm = self.alarms[alarm_id]
            if alarm["Active"]:
                return alarm_id
        return None
            
    async def handle_alarms(self):
        """
        Main alarm handler, all alarm relarted logic should be called from here.
        The alarm execution logic is not included here, it is called right after.
        1. If RESET button is pressed, acknowledge all alarms.
        2. Check if any alarm should be marked as active - this should be after the
           reset to avoid resetting with the gate still open.
        3. Set alarms register values (Set status and UnAck if active was true) and update the OPC UA server.
        4. Check if any alarm status is True. If it is, find the most urgent one.
        5. If any alarm status is True, set trip to True and step to the corresponding error state.
        """
        if self.digital_inputs[DigitalInputs.RST_BUTTON]:
            await self.reset_alarms()
            
        await self.update_alarms_active_state()

        await self.set_alarms()
        alarm_id = await self.check_alarms_and_return_most_urgent()

        if alarm_id:
            self.trip = True
            self.step = self.map_alarm_to_step[alarm_id]

    async def execute_control_logic(self):
        """
        Main logic, it works in the cyclic way:
        1. Read and update inputs.
        2. Check if any alarm should be handled (active, acknowledged, etc.).
        3. Execute the GRAFCET based on the current step and inputs.
        4. Write outputs to the server.
        """
        #NOTE: All variables moved to the constructor.
        prev_step = "unknown" #TODO: REMOVE
        try:
            while True:
                # Updating inputs from server
                await self.update_inputs()

                # Handle all alarms, mark proper 
                await self.handle_alarms()

                # Implement GRAFCET logic:
                #   This should follow a state machine approach, where each state is defined by the current conditions of the inputs and outputs.
                #   The step and transition logic should be implemented here.
                #   For example, if a certain condition is met, change the step to "Start" or "Stop", etc.
                if self.trip:
                    # Error handling logic
                    if self.step == Steps.ERROR_A0:
                        # Handle Tank Level Too High Alarm
                        self.common_operations_handler.stop_system()
                        self.digital_outputs[DigitalOutputs.DISCHARGING_GATE_OPEN] = True

                    elif self.step == Steps.ERROR_A1:
                        # Handle Tank Level Too Low Alarm
                        self.common_operations_handler.stop_system()

                    elif self.step == Steps.ERROR_A2:
                        # Handle Fluid Temperature Too High Alarm 
                        self.common_operations_handler.stop_heating_open_gate()

                    elif self.step == Steps.ERROR_A3:
                        # Handle Fluid Temperature Too Low Alarm
                        self.common_operations_handler.stop_fluid_flow_open_gate()

                    elif self.step == Steps.ERROR_A4:
                        # Handle Discharging Door Open Alarm 
                        self.common_operations_handler.stop_system()
                    
                    elif self.step == Steps.ERROR_A5:
                        self.common_operations_handler.stop_system()
                        self.digital_outputs[DigitalOutputs.DISCHARGING_GATE_OPEN] = True
                else:
                    # Normal operation logic - executed only if no alarm status is True
                    if self.transitions.stop_requested():
                        self.common_operations_handler.stop_system()
                        self.step = Steps.STOP

                    elif self.step == Steps.STOP:
                        if self.transitions.start_button_pressed_and_gate_closed():
                            self.step = Steps.PREFILLING

                    elif self.step == Steps.PREFILLING:
                        if self.transitions.tank_reached_low_level():
                            self.digital_outputs[DigitalOutputs.FILLING_VALVE_OPEN] = False
                            self.step = Steps.INITIALISED
                        else:
                            self.digital_outputs[DigitalOutputs.FILLING_VALVE_OPEN] = True

                    elif self.step == Steps.INITIALISED:
                        if self.transitions.run_button_pressed():
                            self.step = Steps.FILLING

                    elif self.step == Steps.FILLING:
                        if self.transitions.tank_reached_high_level():
                            self.digital_outputs[DigitalOutputs.FILLING_VALVE_OPEN] = False
                            self.step = Steps.HEATING
                        else:
                            self.digital_outputs[DigitalOutputs.FILLING_VALVE_OPEN] = True

                    elif self.step == Steps.HEATING:
                        if self.transitions.temperature_reached_setpoint():
                            self.digital_outputs[DigitalOutputs.HEATING_ON] = False
                            self.step = Steps.DISCHARGING_VALVE
                        else:
                            self.digital_outputs[DigitalOutputs.HEATING_ON] = True

                    elif self.step == Steps.DISCHARGING_VALVE:
                        if self.transitions.tank_back_to_low_level():
                            self.digital_outputs[DigitalOutputs.DISCHARGING_VALVE_OPEN] = False
                            self.step = Steps.FILLING
                        else:
                            self.digital_outputs[DigitalOutputs.DISCHARGING_VALVE_OPEN] = True
                
                if self.step != prev_step:
                    print(f" --- state changed to {self.step} --- ")
                    prev_step = self.step

                # Implement output logic:
                #   This should set the digital outputs based on the current step and alarm conditions.
                #   For example, the output is True when step is "Start" and no alarm is active.
                ...

                # Setting outputs on server
                await self.write_outputs()

                # Sleeping for cycle time
                await asyncio.sleep(self.CYCLE_TIME)
        finally:
            await self.server.stop()
            print("Stopping server")

    
    async def set_opcua_server(self):
        self.server = Server()
        await self.server.init() 
        self.server.set_endpoint("opc.tcp://localhost:7000/freeopcua/server/")

        # setup our own namespace, not really necessary but should as spec
        uri = "http://examples.freeopcua.github.io"
        self.idx = await self.server.register_namespace(uri)

        # get Objects node, this is where we should put our nodes
        objects = self.server.get_objects_node()

        # populating our address space
        self.myobj = await objects.add_object(self.idx, "myPLC")
        
        # For me key is enum, I have to refer to key.value to get the string value
        for key, value in self.digital_inputs.items():
            myvar = await self.myobj.add_variable(self.idx, key.value, value)
            await myvar.set_writable()
        for key, value in self.analog_inputs.items():
            myvar = await self.myobj.add_variable(self.idx, key.value, value)
            await myvar.set_writable()
        for key, value in self.digital_outputs.items():
            myvar = await self.myobj.add_variable(self.idx, key.value, value)
            await myvar.set_writable()
        for key, values in self.alarms.items():
            myalarm = await self.myobj.add_object(self.idx, key.value)
            for newkey, value in values.items():
                myvar = await myalarm.add_variable(self.idx, newkey, value)
                await myvar.set_writable()

        # starting!
        await self.server.start()
        print("Server started")

    async def stop(self):
        await self.server.stop()
        
    
    async def main(self):
        # Set OPC UA server
        await self.set_opcua_server()

        # Execute cycle program
        await self.execute_control_logic()

if __name__ == "__main__":
    plc = PLCSimulator()
    try:
        asyncio.run(plc.main())
    except KeyboardInterrupt:
        print("PLC stopped")



