
from asyncua import Server, ua
import asyncio

class PLCSimulator:
    def __init__(self):
        # Initialize input/output and alarm registers. Complete the registers with the needed signals 
        self.digital_inputs = {"DI0": False}
        self.analog_inputs = {}
        self.digital_outputs = {"DQ0": False}
        # Alarms have Active, UnAck ("Unacknowledged"), and Status attributes
        #   Active: True if the alarm is active, False otherwise
        #   UnAck: True if the alarm is unacknowledged after it was triggered
        #   Status: True if the alarm is either active or unacknowledged
        self.alarms = {"A0": {"Active": False, "UnAck": False, "Status": False}} 
        
        # Time interval for cyclic execution (in seconds)
        self.cycle_time = 0.2
        
    async def update_inputs(self):
        # Update digital input readings from the OPC UA server
        for name in self.digital_inputs.keys():
            myvar = await self.myobj.get_child(f"{self.idx}:{name}")
            value = await myvar.read_value()
            self.digital_inputs.update({name:value})
        # Complete the code to update the analog input readings from the server
        ...

        

    async def write_outputs(self):
        # Complete the necessary code to write the output values into the OPC UA server
        ...

    async def set_alarms(self):
        for key, values in self.alarms.items():
            myalarm = await self.myobj.get_child(f"{self.idx}:{key}")
            # If the alarm is active, set UnAck and Status to True
            if values["Active"]:
                values["UnAck"] = True
                values["Status"] = True
            # Write the values to the OPC UA server
            for newkey, value in values.items():
                myvar = await myalarm.get_child(f"{self.idx}:{newkey}")
                await myvar.write_value(value)

    async def reset_alarms(self):
        # Reset all alarms to inactive and acknowledged
        for key in self.alarms.keys():
            self.alarms[key].update({"UnAck":False})
            self.alarms[key].update({"Status":False})

    
    async def execute_control_logic(self):
        # Initialize variables as needed
        step = "Stop"
        trip = False
        SETPOINT = 45.0
        MAX_TEMPERATURE = 80.0
        MIN_TEMPERATURE = 10.0
        # Add any other necessary variables here
        ...

        try:
            while True:
                # Updating inputs from server
                await self.update_inputs()

                # Implement alarm logic
                # (Example) Tank level too high
                self.alarms["A0"]["Active"] = self.digital_inputs["DI8"]
                # Add more alarms here...

                # Press RESET for ack.
                if self.digital_inputs["DI4"]:
                    await self.reset_alarms()
                        
                # Setting alarms register values and update the OPC UA server
                await self.set_alarms()

                # Implement GRAFCET logic:
                #   This should follow a state machine approach, where each state is defined by the current conditions of the inputs and outputs.
                #   The step and transition logic should be implemented here.
                #   For example, if a certain condition is met, change the step to "Start" or "Stop", etc.
                ...

                # Implement output logic:
                #   This should set the digital outputs based on the current step and alarm conditions.
                #   For example, the output is True when step is "Start" and no alarm is active.
                ...

                # Setting outputs on server
                await self.write_outputs()
                # Sleeping for cycle time
                await asyncio.sleep(self.cycle_time)
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
        
        for key, value in self.digital_inputs.items():
            myvar = await self.myobj.add_variable(self.idx, key, value)
            await myvar.set_writable()
        for key, value in self.analog_inputs.items():
            myvar = await self.myobj.add_variable(self.idx, key, value)
            await myvar.set_writable()
        for key, value in self.digital_outputs.items():
            myvar = await self.myobj.add_variable(self.idx, key, value)
            await myvar.set_writable()
        for key, values in self.alarms.items():
            myalarm = await self.myobj.add_object(self.idx, key)
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



