import asyncio
import pytest
import pytest_asyncio

from src.plc_client import PLCClient
from src.plc_io_definitions import AnalogInputs, DigitalInputs, DigitalOutputs
from src.plc_utils import Alarms, Steps
from tests.helpers_test import (
    DEFAULT_TIMEOUT,
    move_plc_to_desired_step,
    reset_plc_to_clean_stop_state,
    assert_proper_alarm_a0_reaction,
    assert_proper_alarm_a1_reaction,
    assert_proper_alarm_a2_reaction,
    assert_proper_alarm_a3_reaction,
    assert_proper_alarm_a4_reaction,
    assert_proper_alarm_a5_reaction,
    assert_all_alarms_off,
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

@pytest.mark.asyncio
async def test_alarm_priority_enforcement_low_to_high_priority(plc: PLCClient):
    """
    When multiple alarms are active, the one with highest priority should dominate.
    Full priority order (from highest to lowest priority):
        1. Emergency Stop (A5)
        2. Tank Too High (A0)
        3. Temp Too High (A2)
        4. Tank Too Low (A1)
        5. Temp Too Low (A3)
        6. Door Open (A4)

    This test triggers all alarms from the lowest to the highest priority and checks if the
    expected alarm is active. It also checks if the alarms are cleared in the correct order.

    NOTE: Since PLC does not publish the current step, the best way to check if the
    behavior is correct is to check if the values are as expected when the certain alarm
    was triggered. Not the dream solution, but the best I can do now.
    """
    # Move to a known running state
    await move_plc_to_desired_step(plc, Steps.FILLING)

    # Activate all alarms in reverse priority (lowest to highest), every alarm should be
    # triggered when the condition is met.
    await plc.set_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value, False)  # A4
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.DOOR_OPEN.value)

    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 5.0)          # A3
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_LOW.value)

    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, False)            # A1
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_LOW.value)

    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 99.0)         # A2
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_HIGH.value)

    await plc.set_object_value(DigitalInputs.HH_LVL_SENSOR.value, True)             # A0
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_HIGH.value)

    await plc.set_object_value(DigitalInputs.ES_BUTTON.value, True)                 # A5 (top priority)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.ES_PRESSED.value)

    await asyncio.sleep(DEFAULT_TIMEOUT)

    # All alarms should be still active
    assert await plc.get_alarm_status(Alarms.DOOR_OPEN.value)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_LOW.value)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_LOW.value)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_HIGH.value)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_HIGH.value)   

    # A5 should dominate, since step is not explicitily available from the outside validate if
    # behavior is correct by checking the values expected when ES was triggered.
    await assert_proper_alarm_a5_reaction(plc)

    # One by one clearing of alarms to check fallback priority handling

    # Clear Emergency Stop (A5), expect A0 to take over
    await plc.set_object_value(DigitalInputs.ES_BUTTON.value, False)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a0_reaction(plc)

    # Clear A0 -> expect A2 to take over
    await plc.set_object_value(DigitalInputs.HH_LVL_SENSOR.value, False)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a2_reaction(plc)

    # Clear A2 -> expect A1
    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 40.0)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a1_reaction(plc)

    # Clear A1 -> expect A3
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, True)
    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 5.0) # This has to be manually set as it was cleared with A2 clearing
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a3_reaction(plc)

    # Clear A3 -> expect A4
    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 20.0)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a4_reaction(plc)

    # Clear A4
    await plc.set_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # All alarms be cleared
    await assert_all_alarms_off(plc)


@pytest.mark.asyncio
async def test_alarm_priority_enforcement_high_to_low_priority(plc: PLCClient):
    """
    Same as the previous test, but this time alarms are triggered in the order of
    highest to lowest priority.
    """
    await move_plc_to_desired_step(plc, Steps.FILLING)

    await plc.set_object_value(DigitalInputs.ES_BUTTON.value, True) # A5
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.ES_PRESSED.value)
    await assert_proper_alarm_a5_reaction(plc)

    await plc.set_object_value(DigitalInputs.HH_LVL_SENSOR.value, True) # A0
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_HIGH.value)

    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 99.0) # A2
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_HIGH.value)

    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, False) # A1
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_LOW.value)

    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 5.0) # A3
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_LOW.value)

    await plc.set_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value, False) # A4
    await asyncio.sleep(DEFAULT_TIMEOUT)
    assert await plc.get_alarm_status(Alarms.DOOR_OPEN.value)

    # All alarms should be active
    assert await plc.get_alarm_status(Alarms.DOOR_OPEN.value)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_LOW.value)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_LOW.value)
    assert await plc.get_alarm_status(Alarms.TEMP_TOO_HIGH.value)
    assert await plc.get_alarm_status(Alarms.TANK_TOO_HIGH.value)   

    # A5 should dominate
    await assert_proper_alarm_a5_reaction(plc)

    # Reset has no effect while A5 is active
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await assert_proper_alarm_a5_reaction(plc)

    # Clear A5
    await plc.set_object_value(DigitalInputs.ES_BUTTON.value, False)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # A0 should now dominate
    await assert_proper_alarm_a0_reaction(plc)

    # Clean all
    await plc.set_object_value(DigitalInputs.HH_LVL_SENSOR.value, False)
    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 20.0)
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, True)
    await plc.set_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value, True)
    await asyncio.sleep(DEFAULT_TIMEOUT)
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    await assert_all_alarms_off(plc)
