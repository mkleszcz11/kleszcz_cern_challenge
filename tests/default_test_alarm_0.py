##############################
# IMPORTANT NOTE
#
# Name does not start with test_ on purpose.
#
# This test is just to validate, that reference
# by alarm number is still working in case if my code will
# be passed to some sort of automatic benchmarking.
#
# This test works only if the simulator was just started
#
# Alarm 0 is tested in detail in test_alarm_0.py.
##############################

import asyncio
import pytest
import pytest_asyncio

from src.plc_client import PLCClient

SERVER_URL = "opc.tcp://localhost:7000/freeopcua/server/"
CLIENT_TIMEOUT = 5  # seconds

@pytest_asyncio.fixture()
async def plc() -> PLCClient:
    """ Instance of the OPC UA client to communicate with the simulator """
    plc = PLCClient(url=SERVER_URL, timeout=CLIENT_TIMEOUT)
    await plc.init()

    # Set initial conditions here:
    # Stop
    await plc.set_object_pulse("DI0") # Pressed START button
    await asyncio.sleep(1)
    # PreFilling
    await plc.set_object_value("DI5", True) # Minimum levels reached
    await plc.set_object_value("DI6", True)
    await asyncio.sleep(1)
    # Ready
    await plc.set_object_pulse("DI4") # First Reset errors for a clean start
    await asyncio.sleep(1)
    await plc.set_object_pulse("DI1") # Pressed RUN button
    await asyncio.sleep(1)
    # Filling...

    # Yield fixture
    yield plc

    # Disconnect
    await plc.disconnect()

# Trigger overfilling condition
@pytest.mark.asyncio
async def test_fillingheating_overfilling(plc: PLCClient):
    # Assert initial conditions
    assert await plc.get_object_value("DQ0") == True # Tank was filling
    
    # Simulate overfilling condition
    await plc.set_object_value("DI8", True) # Overfilling sensor active
    await asyncio.sleep(1) # Waiting for reactions

    # Assert actuations after overfilling condition
    assert await plc.get_object_value("DQ0") == False # Tank stopped filling
    assert await plc.get_alarm_status("A0") == True # Alarm is triggered
    assert await plc.get_object_value("DQ3") == True # Discharging gate is open

    # Cleanup conditions here:
    

