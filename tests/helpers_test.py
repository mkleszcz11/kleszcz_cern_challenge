#################################
# Collection of helper functions
# for testing PLC functionality.
#################################

import asyncio
from src.plc_utils import Alarms, Steps
from src.plc_io_definitions import AnalogInputs, DigitalInputs, DigitalOutputs
from src.plc_client import PLCClient

# Timeout asyncio should sleep after, for instance, pressing a button.
# Deafault was 1 second.
DEFAULT_TIMEOUT = 0.1

async def assert_all_alarms_off(plc: PLCClient):
    for alarm in Alarms:
        assert await plc.get_alarm_status(alarm.value) == False


async def assert_proper_alarm_a0_reaction(plc: PLCClient):
    """
    Assert expected state when A0 alarm is active (Tank Too High):
    - Filling valve closed
    - Discharging valve closed
    - Discharging gate open
    """
    assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == False


async def assert_proper_alarm_a1_reaction(plc: PLCClient):
    """
    Helper function to assert expected state when A1 alarm status is True.
    From instructions:
    "Prompts an immediate stop to prevent the tank from running dry."
    I assumed that it simply means:
    - Filling valve closed
    - Discharging valve closed (not gate)
    """
    assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False


async def assert_proper_alarm_a2_reaction(plc: PLCClient):
    """
    Assert expected state when A2 alarm is active (Temp Too High):
    - Heating off
    - Discharging gate open
    """
    assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == True


async def assert_proper_alarm_a3_reaction(plc: PLCClient):
    """
    Assert expected state when A3 alarm is active (Temp Too Low).
    By "Stops the fluid flow to prevent the discharge of inadequately heated fluid."
    I understand it as closing the filling and discharging valves.
    - Discharging valve closed
    - Filling valve closed
    - Discharging gate open
    """
    assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == False


async def assert_proper_alarm_a4_reaction(plc: PLCClient):
    """
    Assert expected state when A4 is active (Discharging Door Open):
    - All valves should be off
    """
    assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value) == False


async def assert_proper_alarm_a5_reaction(plc: PLCClient):
    """
    Assert expected state when A5 (Emergency Stop) is active:
    - All actuators off
    """
    assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == False


async def set_default_inputs(plc: PLCClient):
    """
    Set all digital and analog inputs to default 'STOP' state values.
    """
    async with asyncio.TaskGroup() as tg:
        tg.create_task(plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, False))
        tg.create_task(plc.set_object_value(DigitalInputs.L_LVL_SENSOR.value, False))
        tg.create_task(plc.set_object_value(DigitalInputs.H_LVL_SENSOR.value, False))
        tg.create_task(plc.set_object_value(DigitalInputs.HH_LVL_SENSOR.value, False))
        tg.create_task(plc.set_object_value(DigitalInputs.DISCHARGING_GATE_CLOSED.value, True))
        tg.create_task(plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 20.0))
        tg.create_task(plc.set_object_value(DigitalInputs.ES_BUTTON.value, False))


async def press_start_run_stop(plc: PLCClient):
    """
    Press START, RUN, and STOP buttons in sequence.
    Useful for asserting these inputs are ignored during alarm states.
    """
    async with asyncio.TaskGroup() as tg:
        tg.create_task(plc.set_object_pulse(DigitalInputs.START_BUTTON.value))
        tg.create_task(plc.set_object_pulse(DigitalInputs.RUN_BUTTON.value))
        tg.create_task(plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value))


async def reset_plc_to_clean_stop_state(plc: PLCClient):
    """
    Reset the PLC to a clean STOP state with no alarms or active processes.
    """
    # Set default input values
    await set_default_inputs(plc)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # Set default input values
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # STOP button pressed - stop any operation if ongoing
    await plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)


async def wait_until_expected_output(plc: PLCClient,
                                     output: DigitalOutputs,
                                     expected_out: bool,
                                     timeout=5.0,
                                     poll_interval=0.1):
    """
    Wait until a specific digital output reaches the expected boolean value.

    Args:
        plc: The PLC client instance.
        output: DigitalOutputs enum member.
        expected_out: True or False, the desired output state.
        timeout: Maximum time to wait [s].
        poll_interval: Time between checks [s]].
    """
    time_passed = 0.0
    while True:
        if time_passed >= timeout:
            raise TimeoutError(
                f"Timeout: Output {output.name} did not change to {expected_out} within {timeout}s."
            )

        current_val = await plc.get_object_value(output.value)
        if current_val == expected_out:
            return
        await asyncio.sleep(poll_interval)
        time_passed += poll_interval


async def move_plc_to_desired_step(plc: PLCClient, step: Steps):
    """
    Move the PLC to the desired step from normal operation. PLC follows GRAFCET,
    so it is needed to pass all of the intermediate steps to reach the desired one.
    Assumes PLC starts from STOP with no alarms, tank is empty, discharge gate closed.
    """
    # STOP
    if step == Steps.STOP:
        return

    # PREFILLING
    await plc.set_object_pulse(DigitalInputs.START_BUTTON.value)
    await wait_until_expected_output(plc, DigitalOutputs.FILLING_VALVE_OPEN, True)
    if step == Steps.PREFILLING:
        return

    # INITIALISED
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, True)
    await plc.set_object_value(DigitalInputs.L_LVL_SENSOR.value, True)
    await wait_until_expected_output(plc, DigitalOutputs.FILLING_VALVE_OPEN, False)
    if step == Steps.INITIALISED:
        return

    # FILLING
    await plc.set_object_pulse(DigitalInputs.RUN_BUTTON.value)
    await wait_until_expected_output(plc, DigitalOutputs.FILLING_VALVE_OPEN, True)
    if step == Steps.FILLING:
        return

    # HEATING
    await plc.set_object_value(DigitalInputs.H_LVL_SENSOR.value, True)
    await wait_until_expected_output(plc, DigitalOutputs.HEATING_ON, True)
    if step == Steps.HEATING:
        return

    # DISCHARGING_VALVE
    await plc.set_object_value(AnalogInputs.TEMPERATURE_SENSOR.value, 46.0)
    await wait_until_expected_output(plc, DigitalOutputs.DISCHARGING_VALVE_OPEN, True)
    if step == Steps.DISCHARGING_VALVE:
        return

    raise ValueError(f"Unsupported target step: {step}")
