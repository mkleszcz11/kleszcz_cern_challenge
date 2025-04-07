import asyncio
import pytest
import pytest_asyncio

from src.plc_client import PLCClient
from src.plc_io_definitions import DigitalInputs, DigitalOutputs
from src.plc_utils import Alarms, Steps

from tests.helpers_test import (
    assert_all_alarms_off,
    DEFAULT_TIMEOUT,
    move_plc_to_desired_step,
    press_buttons_at_once,
    reset_plc_to_clean_stop_state,
    assert_proper_alarm_a5_reaction,
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

async def simulate_and_validate_a5(plc: PLCClient):
    """
    Simulate and validate alarm A5:
    1. Trigger ES button
    2. Validate emergency stop behavior
    3. Pressing buttons should have no effect (excluding ES)
    4. Reset fails if button still active
    5. Release button
    6. Reset clears alarm
    """
    await plc.set_object_value(DigitalInputs.ES_BUTTON.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    await assert_proper_alarm_a5_reaction(plc)
    assert await plc.get_alarm_status(Alarms.ES_PRESSED.value) == True

    await press_buttons_at_once(plc)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a5_reaction(plc)

    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.ES_PRESSED.value) == True

    await plc.set_object_value(DigitalInputs.ES_BUTTON.value, False)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.ES_PRESSED.value) == False
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
async def test_a5_from_selected_states(plc, step):
    """
    Test A5 (Emergency Stop) triggered from all operational states.
    """
    await move_plc_to_desired_step(plc, step)
    await simulate_and_validate_a5(plc)
