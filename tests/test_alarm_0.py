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
    press_start_run_stop,
    reset_plc_to_clean_stop_state,
    assert_proper_alarm_a0_reaction,
)

SERVER_URL = "opc.tcp://localhost:7000/freeopcua/server/"
CLIENT_TIMEOUT = 5  # seconds

@pytest_asyncio.fixture()
async def plc() -> PLCClient:
    plc = PLCClient(url=SERVER_URL, timeout=CLIENT_TIMEOUT)
    await plc.init()

    # Start every test from the STOP state with innitial values and no alarms.
    await reset_plc_to_clean_stop_state(plc)

    # Yield fixture
    yield plc

    # Disconnect
    await plc.disconnect()

async def simulate_and_validate_a0(plc: PLCClient):
    """
    This simultes triggering the alarm, validates the system response and reset the alarm.
    Test cases are used to set up the scenario and then they are calling this function.
    1. Trigger HH level
    2. Validate outputs and alarm state
    3. Pressing START, RUN, STOP buttons should have no effect
    4. Reset attempt while condition persists (should not clear alarm)
    5. Clear condition
    6. Reset again (should succeed)
    """
    # 1. Simulate water level too high
    await plc.set_object_value(DigitalInputs.HH_LVL_SENSOR.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # 2. Assert correct system response
    await assert_proper_alarm_a0_reaction(plc)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_HIGH.value) == True

    # 3. Inputs should be ignored
    await press_start_run_stop(plc)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a0_reaction(plc)

    # 4. Reset the alarm (should fail, sensor still high)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a0_reaction(plc)

    # 5. Lower the sensor signal
    await plc.set_object_value(DigitalInputs.HH_LVL_SENSOR.value, False)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Alarm still active until reset
    assert await plc.get_alarm_status(Alarms.TANK_TOO_HIGH.value) == True

    # 6. Reset alarm (should now clear)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_HIGH.value) == False
    await assert_all_alarms_off(plc)

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "step", [
        Steps.STOP,
        Steps.PREFILLING,
        Steps.INITIALISED,
        Steps.FILLING,
        Steps.HEATING,
        Steps.DISCHARGING_VALVE
    ]
)
async def test_a0_from_selected_states(plc, step):
    """
    Test A0 triggered across all operational states
    """
    await move_plc_to_desired_step(plc, step)
    await simulate_and_validate_a0(plc)
