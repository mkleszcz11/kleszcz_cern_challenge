import asyncio
import pytest
import pytest_asyncio

from src.plc_client import PLCClient
from src.plc_utils import Steps
from src.plc_io_definitions import DigitalInputs, DigitalOutputs, AnalogInputs

from tests.helpers_test import (
    DEFAULT_TIMEOUT,
    move_plc_to_desired_step,
    reset_plc_to_clean_stop_state,
    assert_all_buttons_off,
    assert_lvl_sensor_states,
    press_buttons_at_once,
    assert_system_stopped,
)

# Idea behind these tests:
# Each test focuses on a single, specific state transition. Since the PLC behaves as a state machine,
# we must first move the system into the desired initial state before triggering a transition.
# This setup is handled using helper functions for consistency and clarity.
#
# Once the target start state is reached, the current output states are asserted to ensure the system
# is behaving as expected. Then, the transition is triggered, and the resulting outputs are again
# thoroughly validated to confirm correct behavior.
#
# This tests should be very very explicit, to leave no room for guessing. Since the PLC I/O space is
# not that big, we can check manually entire device "snapshots" before the transition (done partially 
# through helper functions to reduce code duplication) and after the transition.
#
# TL;DR:
# 1. Move to the desired start state
# 2. Assert all outputs match the expected values
# 3. Trigger the transition
# 4. Assert all outputs match the expected values after the transition
#
# NOTE: I know I should use something smarter to check if device snapshot is correct (like crating
# a dict and ding some helper function to helpers_test.py), but it is already almost 02:00 AM and
# tomorrow I have to go the the lab and to the airport afterwards :(

SERVER_URL = "opc.tcp://localhost:7000/freeopcua/server/"
CLIENT_TIMEOUT = 5  # seconds

@pytest_asyncio.fixture()
async def plc() -> PLCClient:
    """Instance of the OPC UA client to communicate with the simulator."""
    plc = PLCClient(url=SERVER_URL, timeout=CLIENT_TIMEOUT)
    await plc.init()
    await reset_plc_to_clean_stop_state(plc)
    yield plc
    await plc.disconnect()


# Press START button and check that tank is filling
@pytest.mark.asyncio
async def test_start_prefilling(plc: PLCClient):
    """
    Simulate pressing the START button.

    Start state:     STOP
    Action:          Press START button.
    Expected result: Filling valve should open, tank should start filling.
    
    Additional check: Try to press RUN, STOP, RST buttons - should have no effect.
    """
    async def assert_start_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == False # Tank is not filling
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False # Tank is not discharging
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True  # Gate is closed (motor)
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False # Heating is off
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True  # Discharging gate is closed (sensor)
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0  # Temperature sensor show 20 degrees
        await assert_lvl_sensor_states(plc, LL=False, L=False, H=False, HH=False)               # Low and high level sensors are off
        await assert_all_buttons_off(plc)                                                       # All buttons are off

    async def assert_finish_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == True  # Tank is filling
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False 
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0
        await assert_lvl_sensor_states(plc, LL=False, L=False, H=False, HH=False)
        await assert_all_buttons_off(plc)

    # Move to the desired start state
    await move_plc_to_desired_step(plc, Steps.STOP)

    # Assert start conditions
    await assert_start_test_conditions()

    # Additional check, press unrelated buttons
    await press_buttons_at_once(plc, run_bt=True, stop_bt=True, reset_bt=True, start_bt=False)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_start_test_conditions()

    # Simulate pressing the START button
    await plc.set_object_pulse(DigitalInputs.START_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Assert that only the filling valve is open, rest is unchanged
    await assert_finish_test_conditions()


# Test low level has been reached
@pytest.mark.asyncio
async def test_prefilling_ready(plc: PLCClient):
    """
    Simulate low level sensor reached.

    Start state:     PREFILLING
    Action:          LowLow level and Low level sensors becomes True.
    Expected result: Filling valve should close (system enters INITIALISED).
    
    Additional check I: Try to press RUN, START, RST buttons - should have no effect.
    Additional check II: At the end press STOP button - should stop everything.
    """
    async def assert_start_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == True  # Filling should be in progress
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False # Tank is not discharging
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True  # Gate is closed (motor)
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False # Heating is off
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True  # Gate is closed (sensor)
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0  # Default temp
        await assert_lvl_sensor_states(plc, LL=False, L=False, H=False, HH=False)
        await assert_all_buttons_off(plc)

    async def assert_finish_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == False # Filling stopped
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0
        await assert_lvl_sensor_states(plc, LL=True, L=True, H=False, HH=False)
        await assert_all_buttons_off(plc)

    # Move to PREFILLING state
    await move_plc_to_desired_step(plc, Steps.PREFILLING)

    # Validate initial PREFILLING conditions
    await assert_start_test_conditions()

    # Additional check, press unrelated buttons
    await press_buttons_at_once(plc, run_bt=True, stop_bt=False, reset_bt=True, start_bt=True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_start_test_conditions()

    # Trigger low level detection
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, True)
    await plc.set_object_value(DigitalInputs.L_LVL_SENSOR.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Validate system transitioned to INITIALISED
    await assert_finish_test_conditions()
    
    # Additional check II, press STOP button
    await plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_system_stopped(plc)


# Test RUN button pressed
@pytest.mark.asyncio
async def test_run_button_filling(plc: PLCClient):
    """
    Simulate pressing the RUN button.

    Start state:     INITIALISED (tank filled to low level)
    Action:          Press RUN button.
    Expected result: Filling valve should open again (system enters FILLING).

    Additional check I: Try to press START, RST buttons - should have no effect.
    Additional check II: At the end press STOP button - should stop everything.
    """
    async def assert_start_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == False # Filling off
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0
        await assert_lvl_sensor_states(plc, LL=True, L=True, H=False, HH=False)
        await assert_all_buttons_off(plc)

    async def assert_finish_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == True  # Filling restarted
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0
        await assert_lvl_sensor_states(plc, LL=True, L=True, H=False, HH=False)
        await assert_all_buttons_off(plc)

    # Move to INITIALISED step (tank filled to low level)
    await move_plc_to_desired_step(plc, Steps.INITIALISED)

    # Validate preconditions
    await assert_start_test_conditions()

    # Additional check I, try pressing unrelated buttons
    await press_buttons_at_once(plc, run_bt=False, stop_bt=False, reset_bt=True, start_bt=True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_start_test_conditions()

    # Press RUN to resume filling
    await plc.set_object_pulse(DigitalInputs.RUN_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Check that filling valve is now open
    await assert_finish_test_conditions()
    
    # Additional check II, press STOP button
    await plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_system_stopped(plc)


# Test high level has been reached
@pytest.mark.asyncio
async def test_high_level_heating(plc: PLCClient):
    """
    Reaching high level should stop filling and start heating.

    Start state:     FILLING
    Action:          High level sensor becomes True.
    Expected result: Filling valve should close, heating should start (system enters HEATING).

    Additional check I: Try to press START, RUN, RST buttons - should have no effect.
    Additional check II: At the end press STOP button - should stop everything.
    """
    async def assert_start_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == True  # Filling in progress
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0
        await assert_lvl_sensor_states(plc, LL=True, L=True, H=False, HH=False)
        await assert_all_buttons_off(plc)

    async def assert_finish_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == False  # Filling stopped
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == True   # Heating started
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0
        await assert_lvl_sensor_states(plc, LL=True, L=True, H=True, HH=False)
        await assert_all_buttons_off(plc)

    # Move to FILLING step (tank is being filled above low level)
    await move_plc_to_desired_step(plc, Steps.FILLING)

    # Assert initial filling conditions
    await assert_start_test_conditions()

    # Additional check I, press unrelated buttons
    await press_buttons_at_once(plc, run_bt=True, stop_bt=False, reset_bt=True, start_bt=True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_start_test_conditions()

    # Trigger high level sensor
    await plc.set_object_value(DigitalInputs.H_LVL_SENSOR.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Validate heating state
    await assert_finish_test_conditions()
    
    # Additional check II, press STOP button
    await plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_system_stopped(plc)


# Test setpoint has been reached
@pytest.mark.asyncio
async def test_setpoint_discharging_valve(plc: PLCClient):
    """
    When heating setpoint is reached, heating stops and discharging starts.

    Start state:     HEATING
    Action:          Temperature reaches or exceeds setpoint (45.0°C).
    Expected result: Heating turns off, discharging valve opens (system enters DISCHARGING_VALVE).

    Additional check I: Try to press START, RUN, RST buttons - should have no effect.
    Additional check II: At the end press STOP button - should stop everything.
    """
    async def assert_start_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == False  # Not filling
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False  # Not discharging
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == True   # Heating in progress
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       <= 45.0
        await assert_lvl_sensor_states(plc, LL=True, L=True, H=True, HH=False)
        await assert_all_buttons_off(plc)

    async def assert_finish_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == True   # Discharging started
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False  # Heating stopped
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       >  45.0
        await assert_lvl_sensor_states(plc, LL=True, L=True, H=True, HH=False)
        await assert_all_buttons_off(plc)

    # Move to HEATING state (tank is full, heating below setpoint)
    await move_plc_to_desired_step(plc, Steps.HEATING)

    # Assert heating is active
    await assert_start_test_conditions()

    # Additional check I: press unrelated buttons
    await press_buttons_at_once(plc, run_bt=True, stop_bt=False, reset_bt=True, start_bt=True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_start_test_conditions()

    # Simulate temperature reaching setpoint
    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 46.0)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Assert transition to discharging valve state
    await assert_finish_test_conditions()

    # Additional check II: press STOP to end process
    await plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_system_stopped(plc)


# Test low level has been reached
@pytest.mark.asyncio
async def test_back_to_filling(plc: PLCClient):
    """
    Once tank is discharged and low level is reached, filling restarts.

    Start state:     DISCHARGING_VALVE
    Action:          Low level sensor becomes False (tank is emptying).
    Expected result: Discharging valve closes, filling valve opens again (system re-enters FILLING).

    Additional check I: Try to press START, RUN, RST buttons - should have no effect.
    Additional check II: At the end press STOP button - should stop everything.
    """
    async def assert_start_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == True   # Discharging in progress
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       >= 45.0
        await assert_lvl_sensor_states(plc, LL=True, L=True, H=True, HH=False)
        await assert_all_buttons_off(plc)

    async def assert_finish_test_conditions():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == True   # Filling restarted
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False  # Discharging stopped
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       >= 45.0
        await assert_lvl_sensor_states(plc, LL=True, L=False, H=False, HH=False)
        await assert_all_buttons_off(plc)

    # Move to DISCHARGING_VALVE state
    await move_plc_to_desired_step(plc, Steps.DISCHARGING_VALVE)

    # Assert discharging is active
    await assert_start_test_conditions()

    # Additional check I: press unrelated buttons
    await press_buttons_at_once(plc, run_bt=True, stop_bt=False, reset_bt=True, start_bt=True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_start_test_conditions()

    # Simulate tank getting empty (L and H sensor becomes False)
    await plc.set_object_value(DigitalInputs.L_LVL_SENSOR.value, False)
    await plc.set_object_value(DigitalInputs.H_LVL_SENSOR.value, False)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Validate transition back to FILLING
    await assert_finish_test_conditions()

    # Additional check II: press STOP to end process
    await plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_system_stopped(plc)


# # Stop button
# Stop button was already tested in every device step. It is also tested in alarm tests, refer
# to the funcctions called "simulate_and_validate_aX".
# "await press_buttons_at_once(plc)" is always called in the error state

# Add more test cases if needed

@pytest.mark.asyncio
async def test_prefilling_not_yet_ready(plc: PLCClient):
    """
    Simulate low low level sensor reached, but low level sensor is still False.

    Start state:     PREFILLING
    Action:          Only LowLow sensor becomes True (L_LVL_SENSOR remains False).
    Expected result: System must remain in PREFILLING. Filling continues.

    Additional check I: Try to press START, RUN, RST buttons - should have no effect.
    Additional check II: At the end press STOP button - should stop everything.
    """
    async def assert_prefilling_active():
        assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value)     == True   # Still filling
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
        assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True
        assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value)             == False
        assert await plc.get_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value) == True
        assert await plc.get_object_value(AnalogInputs.TEMPERATURE_SENSOR.value)       == 20.0
        await assert_all_buttons_off(plc)

    # Move to PREFILLING state
    await move_plc_to_desired_step(plc, Steps.PREFILLING)

    # Ensure initial PREFILLING state
    await assert_lvl_sensor_states(plc, LL=False, L=False, H=False, HH=False)
    await assert_prefilling_active()

    # Additional check I: press unrelated buttons
    await press_buttons_at_once(plc, run_bt=True, stop_bt=False, reset_bt=True, start_bt=True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_prefilling_active()

    # Trigger only LowLow level sensor (not enough to transition)
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Still not ready: system must remain in PREFILLING
    await assert_prefilling_active()
    await assert_lvl_sensor_states(plc, LL=True, L=False, H=False, HH=False)

    # Additional check II: press STOP to reset system
    await plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_system_stopped(plc)
