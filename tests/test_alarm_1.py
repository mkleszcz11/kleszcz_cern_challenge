import asyncio
import pytest
import pytest_asyncio

from src.plc_client import PLCClient
from src.plc_io_definitions import  AnalogInputs, DigitalInputs, DigitalOutputs
from src.plc_utils import Alarms, Steps

from tests.helpers_test import (
    assert_all_alarms_off,
    DEFAULT_TIMEOUT,
    move_plc_to_desired_step,
    press_buttons_at_once,
    reset_plc_to_clean_stop_state,
    assert_proper_alarm_a1_reaction,
)

SERVER_URL = "opc.tcp://localhost:7000/freeopcua/server/"
CLIENT_TIMEOUT = 5  # seconds

@pytest_asyncio.fixture()
async def plc() -> PLCClient:
    plc = PLCClient(url=SERVER_URL, timeout=CLIENT_TIMEOUT)
    await plc.init()
    await reset_plc_to_clean_stop_state(plc)
    yield plc
    await plc.disconnect()

async def simulate_and_validate_a1(plc: PLCClient):
    """
    This simultes triggering the alarm, validates the system response and reset the alarm.
    Test cases are used to set up the scenario and then they are calling this function.
    1. Low low level sensor reads False
    2. Assert A1 is triggered, system stops
    3. Pressing buttons should have no effect (excluding ES)
    4. Reset should clear the alarm even if sensor is still False.
    """
    # 1. Simulate water level too low
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, False) # No reading for low-low level sensor
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # 2. Assert actuations after overfilling condition, specific alarm is also triggered
    await assert_proper_alarm_a1_reaction(plc)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_LOW.value) == True

    # 3. Try to press start, run, stop - should be no reaction
    await press_buttons_at_once(plc)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a1_reaction(plc) == True

    # 4. Reset the alarm, alarm should be turned off now
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_LOW.value) == False
    await assert_all_alarms_off(plc) # Just make sure that all other alarms are off

@pytest.mark.asyncio
async def test_a1_while_stop(plc: PLCClient):
    """
    A1 triggered when the system is stopped.
    
    LL alarm is triggered by the falling edge, we have to set sensor
    value to True manually in this case
    """
    await move_plc_to_desired_step(plc, Steps.STOP)
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await simulate_and_validate_a1(plc)

@pytest.mark.asyncio
async def test_a1_while_prefilling(plc: PLCClient):
    """
    A1 triggered during pre-filling.
    Same as in the STOP state, LL sensor value has to be set to True manually.
    """
    await move_plc_to_desired_step(plc, Steps.PREFILLING)
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await simulate_and_validate_a1(plc)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "step", [
        Steps.INITIALISED,
        Steps.FILLING,
        Steps.HEATING,
        Steps.DISCHARGING_VALVE
    ]
)
async def test_a1_from_selected_states(plc, step):
    """
    Test A1 triggered across all operational states, except
    for STOP and PREFILLING (due to the falling edge detection).
    """
    await move_plc_to_desired_step(plc, step)
    await simulate_and_validate_a1(plc)
