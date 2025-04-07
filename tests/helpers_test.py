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
DEFAULT_TIMEOUT = 1

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
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_GATE_CLOSE.value) == False


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

async def assert_system_stopped(plc: PLCClient):
    """
    Assert that the system is stopped. We do not consider discharge gate, rest should be
    inactive/closed.
    """
    assert await plc.get_object_value(DigitalOutputs.FILLING_VALVE_OPEN.value) == False
    assert await plc.get_object_value(DigitalOutputs.HEATING_ON.value) == False
    assert await plc.get_object_value(DigitalOutputs.DISCHARGING_VALVE_OPEN.value) == False

async def assert_all_buttons_off(plc: PLCClient):
    """
    Assert all buttons are in 'off' state.
    """
    assert await plc.get_object_value(DigitalInputs.START_BUTTON.value) == False
    assert await plc.get_object_value(DigitalInputs.RUN_BUTTON.value) == False
    assert await plc.get_object_value(DigitalInputs.STOP_BUTTON.value) == False
    assert await plc.get_object_value(DigitalInputs.ES_BUTTON.value) == False
    assert await plc.get_object_value(DigitalInputs.RST_BUTTON.value) == False
        

async def assert_lvl_sensor_states(plc: PLCClient, LL: bool, L: bool, H: bool, HH: bool):
    """
    Assert the states of the level sensors.
    """
    assert await plc.get_object_value(DigitalInputs.LL_LVL_SENSOR.value) == LL
    assert await plc.get_object_value(DigitalInputs.L_LVL_SENSOR.value) == L
    assert await plc.get_object_value(DigitalInputs.H_LVL_SENSOR.value) == H
    assert await plc.get_object_value(DigitalInputs.HH_LVL_SENSOR.value) == HH


async def assert_device_state_changed_only(
    plc: PLCClient,
    previous_state: dict,
    expected_changes: dict,
):
    """
    Assert that only the expected outputs/inputs changed.

    Args:
        plc: PLC client
        previous_state: Full snapshot of relevant state before the action.
        expected_changes: Subset of keys with expected new values.
    """
    for key, old_value in previous_state.items():
        current_value = await plc.get_object_value(key.value)
        expected_value = expected_changes.get(key, old_value)
        assert current_value == expected_value, (
            f"{key.name} changed unexpectedly: expected {expected_value}, got {current_value}"
        )


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


async def press_buttons_at_once(plc: PLCClient,
                                run_bt: bool = True,
                                stop_bt: bool = True,
                                reset_bt: bool = True,
                                start_bt: bool = True):
    """
    Press all specified buttons at once. Do not consider the ES, as it would
    override everything else.
    """
    async with asyncio.TaskGroup() as tg:
        if run_bt:
            tg.create_task(plc.set_object_pulse(DigitalInputs.RUN_BUTTON.value))
        if stop_bt:
            tg.create_task(plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value))
        if reset_bt:
            tg.create_task(plc.set_object_pulse(DigitalInputs.RST_BUTTON.value))
        if start_bt:
            tg.create_task(plc.set_object_pulse(DigitalInputs.START_BUTTON.value))


async def reset_plc_to_clean_stop_state(plc: PLCClient):
    """
    Reset the PLC to a clean STOP state with no alarms or active processes.
    """
    # Set default input values
    await set_default_inputs(plc)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # STOP button pressed - complete reset
    await plc.set_object_pulse(DigitalInputs.STOP_BUTTON.value)
    await asyncio.sleep(DEFAULT_TIMEOUT)

    # RESET button pressed - reset any alarms
    await plc.set_object_pulse(DigitalInputs.RST_BUTTON.value)
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
    
    This is not an exhaustive test for state transitions, this is tested in test_aa_grafcet.py.
    """
    # STOP
    await plc.set_object_value(DigitalInputs.LL_LVL_SENSOR.value, False)
    await plc.set_object_value(DigitalInputs.L_LVL_SENSOR.value, False)
    await plc.set_object_value(DigitalInputs.H_LVL_SENSOR.value, False)
    await plc.set_object_value(DigitalInputs.HH_LVL_SENSOR.value, False)
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
