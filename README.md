# Assumptions:
1. Only one of the following can be true at a time:
    - Tank is charging
    - Tank is heating
    - Tank is discharging

I am assuming this, as it is not explicitly specified in the instruction, that heating should be turned off when the fluid temperature reaches the 45ºC, it is only said `The fluid’s temperature should raise until a setpoint of 45ºC.`. I guess, in reality some controller might keep the desired fluid temperature even while discharging. I treat the tank as a perfect thermal insulator.

2. Initial state:
- Tank is empty (All sensors are `False`)
- Tank is not filling (`DQ0` is `False`)S
- Tank is not heating (`DQ2` is `False`)
- Tank is not discharging via valve (`DQ1` is `False`)
- Tank gate is closed (`DI9` is `True` and `DQ3` is `True`) - This is based on the provided test case `test_start_prefilling`, which I assumed should pass without any changes.
- Sensor reading is 20ºC

Default states explanation:
- Water sensors are `True` when water is detected - based on the hint from instruction `Falling Edge Detection Alarm`
- Gate opens passively, based on the expected behiavior of the Emergency Stop. Therefore, passing `True` to the motor (`DQ3`) makes gate close.
- 

3. Error prriorites:
Error prriorites should be defined as we can imagine, the following scenario (just an example):
    1. Fluid level is too low, alarm is activated
    2. Something weird happens and we have to, for whatever reason, stop execution and open the gate. Low level alarm (with no gate opening) cannot override the emergency stop behavior (shut everything down and open a gate).

Error priorities ranked from highest to lowest - this list is subjective and is propped only by intuition:
- Emergency Stop
- Tank Level Too High Alarm
- Tank Temperature Too High Alarm
- Tank Level Too Low Alarm
- Tank Teperature Too Low Alarm
- Tank Discharging Door Open Alarm

4. `Immidiate response` interpretation. For alarm A0 instruction says: `Initiates an immediate stop of the system to prevent overflow.`. In the provided testcase we are putting a `True` value as High high level reading and then waiting a second, then asserting that the system is stopped. I assumed the same for the other alarms, especially `emergency stop`, instead of trying to make a paraller task that would be checking the alarms and stopping the system, disregarding the cycle time. I assumed it would be a bit of overkill.

5. Test design.
In normal scenario I would propably put all alarm tests in one file as concept for each test is similar, but for readability I decided to split them into separate files.


6. Emergency button is set via `set_object_value`, not `set_object_pulse` to simulate a standard emergency stop (has to be deactivated again with `set_object_value`).

# How to run the code
1. Activate the virtual environment:
```bash
source venv/bin/activate
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Run the tests, for instance:
```bash
pytest tests/test_aa_grafcet.py
```

# Other notes.
1. I have not really utilised parallel programining in this task, as I think it is not really that needed. Project is rather small and doing it in a simplest way looks ok. I can imagine utilising asyncio if we would have to fetch a lot of sensors data in parallel, but since we have only 10 sensors it would just add unnecessary complexity (subjective). Another reason would be to simulate a gate movement, I don't have a state where sensors shows that the gate is open, but the motor is turned on (this state would exist in a real world), but again, I think it would be an overthinking.

2. I had a bit of a trouble deciding how I want my emergency stop to work. In real life I assume it would physically cut the power to the pumps and actuators and halt a system no matter what PLC is doing. Here I just wired it to the cycle time (point 4 in the assumptions).

3. I would love to share links to a few public projects, that are somehow related to this task.
-  Simulated OPC UA elevator controller. I have been working recently with OPC devices at my work. Here is the link to our public simulator, which can simulate vehicles (unrelated to this) and opc elevator, which is actually a very very simple version of what is this challange about. Goal of this simulator is actually not to emulate the actual plc behavious, thus implementation is so simple.
https://gitlab.com/meilirobots/public/python-simulator/-/blob/DEV-3968-Add-elevator-for-master-in-be/main.py?ref_type=heads

-  Student project with a nice implementation of a state machine. Last semester I took a course called "Product Design a Development" at EPFL and we ended up doing a project 

- In my previous job I was working as a low level embedded engineer, therefore structure with a lot of enums as I personally find it quite useful and intuitive. Link to simple file that I had a pleasure to work on:
#TODO
