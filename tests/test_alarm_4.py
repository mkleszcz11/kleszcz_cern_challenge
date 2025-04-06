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
    press_start_run_stop,
    reset_plc_to_clean_stop_state,
    assert_proper_alarm_a4_reaction,
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

async def simulate_and_validate_a4(plc: PLCClient):
    """
    Simulate and validate alarm A4:
    1. Trigger open discharging door sensor
    2. Validate alarm and system shutdown
    3. Inputs ignored
    4. Reset fails if condition persists
    5. Clear input
    6. Reset clears alarm
    """
    await plc.set_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value, False)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    await assert_proper_alarm_a4_reaction(plc)
    assert await plc.get_alarm_status(Alarms.DOOR_OPEN.value) == True

    await press_start_run_stop(plc)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a4_reaction(plc)

    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.DOOR_OPEN.value) == True

    await plc.set_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.DOOR_OPEN.value) == False
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
async def test_a4_from_selected_states(plc, step):
    """
    Test A4 (Discharging Door Open) triggered from all key states.
    """
    await move_plc_to_desired_step(plc, step)
    await simulate_and_validate_a4(plc)
