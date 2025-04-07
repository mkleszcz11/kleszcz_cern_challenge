import asyncio
import pytest
import pytest_asyncio

from src.plc_client import PLCClient
from src.plc_io_definitions import AnalogInputs, DigitalInputs, DigitalOutputs
from src.plc_utils import Alarms, Steps

from tests.helpers_test import (
    assert_all_alarms_off,
    DEFAULT_TIMEOUT,
    move_plc_to_desired_step,
    press_buttons_at_once,
    reset_plc_to_clean_stop_state,
    assert_proper_alarm_a2_reaction,
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

async def simulate_and_validate_a2(plc: PLCClient):
    """
    Trigger and validate A2 (Temperature Too High).
    Steps:
    1. Raise temp above MAX
    2. Validate alarm and outputs
    3. Pressing buttons should have no effect (excluding ES)
    4. Reset (fail, condition persists)
    5. Lower temp
    6. Reset again (succeed)
    """
    # 1. Trigger temperature too high
    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 99.0)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # 2. Assert expected state
    await assert_proper_alarm_a2_reaction(plc)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_HIGH.value) is True

    # 3. Try to press start, run, stop - should be no reaction
    await press_buttons_at_once(plc)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a2_reaction(plc)

    # 4. Reset (fail, sensor still shows high temp)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_HIGH.value) is True

    # 5. Lower temp
    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 40.0)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # 6. Reset (success)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_HIGH.value) is False
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
async def test_a2_from_selected_states(plc, step):
    """
    Test A2 (Temperature Too High) triggered across all operational states.
    """
    await move_plc_to_desired_step(plc, step)
    await simulate_and_validate_a2(plc)
