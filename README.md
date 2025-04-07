# TSC2025-2 SY-EPC-CCS Challenge - Notes and Assumptions

### Author: Marcin Kleszcz

## Assumptions
1. **Only One Action at a Time**  
   The tank can be either:
   - Filling
   - Heating
   - Discharging  
   ...but never more than one simultaneously. I am assuming this, as it is not explicitly specified in the instruction, that heating should be turned off when the fluid temperature reaches the 45ºC, it is only said `The fluid’s temperature should raise until a setpoint of 45ºC.`. I guess, in reality some controller might keep the desired fluid temperature even while discharging. I treat the tank as a perfect thermal insulator.

2. **Initial State**  
   - All sensors are `False` (tank is empty)
   - `DQ0` (Filling valve) is `False`
   - `DQ1` (Discharging valve) is `False`
   - `DQ2` (Heating) is `False`
   - `DQ3` (Gate motor) is `True` – meaning the gate is closed  
   - `DI9` (Gate closed sensor) is `True`
   - Temperature sensor reads 20ºC 

   Notes:
   - Water level sensors are `True` when water is detected.
   - The gate opens passively, based on the expected behiavior of the Emergency Stop. Setting `DQ3 = True` closes it.

3. **Alarm Priorities**  
   In case of multiple active alarms, priority is respected. For example, if the tank is too low, but the emergency stop is activated, the emergency is prioritized.

   Priority order (from highest to lowest):
   1. Emergency Stop
   2. Tank Level Too High
   3. Temperature Too High
   4. Tank Level Too Low
   5. Temperature Too Low
   6. Door Open

4. **"Immediate Stop" Interpretation**  
   For A0 (Tank Level Too High), the instruction says:  
   _"Initiates an immediate stop of the system to prevent overflow."_  
   I interpret this as: update the system on the next PLC cycle. I avoided setting up parallel tasks for instant reaction, which felt excessive for this context.

5. **Emergency Button Handling**  
   The emergency button is activated with `set_object_value`, not `set_object_pulse`, to simulate a persistent emergency state. It must be manually deactivated.

---

## Making tests faster:
At the moment of writing this I execute 45 test cases. With default values it takes 8:30 min. It can be significantly reduced by changing the following values:

- `DEFAULT_TIMEOUT` in `helpers_test.py` (default 1s)
- `CYCLE_TIME` in `PLCSimulator` (default 0.2s)
- `await asyncio.sleep(...)` delays in `plc.py` (default 0.5s)

---

## How to run the code

1. **Create a virtual environment using python 3.11:**
   ```bash
   python3.11 -m venv env

2. **Activate the virtual environment:**
    ```bash
    source env/bin/activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the simulation and tests:**
    Open two terminals. In the first:
    ```bash
    source env/bin/activate
    python3 -m src.plc_simulator
    ```

    In the second:
    ```bash
    source env/bin/activate
    pytest tests
    ```

---

## Additional Notes.
1. **Concurrency**  
   I didn’t use that much asyncio features for this project because it didn’t feel necessary. The system is small, and everything works fine using simple, sequential logic.  
   Async handling might be useful in larger systems, especially when polling many sensors or simulating partial actuator states (like the gate being in motion), but for now it would only add complexity without much benefit.

2. **Emergency Stop Design**  
   I wasn’t sure how to handle the emergency stop at first. In real systems, it would likely cut power physically. Here, I simulate that by stopping everything during the next PLC cycle (as described in Assumption 4).

3. **Test Structure**  
   Normally, I’d put all alarm tests into a single file since they follow the same logic. But for readability and clarity, I split them into separate files.

4. **CI, Linters, and Time**  
   I didn’t add GitHub Actions or pipelines, and I didn’t run the code through linters or formatters. I only had a weekend to complete this, so I focused on the logic and tests. Apologies if the formatting causes any mild eye pain.


5. **Related Work and Context**  
   Below are a few public repositories that I contributed to - in some cases as the main contributor - which are related to this challenge. They help explain some of my design choices and reflect how I approach similar problems:

   - **Pippetifying machine made from 3D printer (Student Project at EPFL)**  
    This is a student project from a course called *Product Design and Development* at EPFL. We used the `state-machine` library to implement a basic state machine instead of building one from scratch. If this PLC project were larger or I had more time, I would likely take a similar approach, as it simplifies the logic.
    https://github.com/mkleszcz11/pipettify

    - **Embedded C influencce**
    In a previous job, I worked as a low-level embedded engineer. That's why I like modelling systems using enums and tables - it helps make logic more readable and maintainable (at least for me).
    Link to a sample file I worked on:
    https://github.com/zephyrproject-rtos/hal_nordic/blob/master/nrfx/hal/nrf_gpio.h

    - **OPC UA Elevator Simulator** 
    I've recently been working with OPC devices at my job. This public simulator can simulate both vehicles (unrelated) and a simple OPC elevator - a very very basic version of what this challenge is about. Its goal was to simulate message flow, not actual PLC behaviour, so the implementation is intentionally minimal.
    https://gitlab.com/meilirobots/public/python-simulator/-/blob/DEV-3968-Add-elevator-for-master-in-be/main.py?ref_type=heads
