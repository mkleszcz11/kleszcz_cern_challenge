##############################
# IMPORTANT NOTE - same as for default_test_alarm_0.py
#
# Name does not start with test_ on purpose.
#
# This test is just to validate, that reference
# by alarm number is still working in case if my code will
# be passed to some sort of automatic benchmarking.
#
# This test works only if the simulator was just started, i prefer to
# run all of them in one go, without stopping the simulator in between.
#
# Tranistions are not tested in detail in test_aa_grafcet.py.
# They are also tested in all alarms tests, but this is not
# the main focus of these tests.
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
    yield plc
    await plc.disconnect()

# Press START button and check that tank is filling
@pytest.mark.asyncio
async def test_start_prefilling(plc: PLCClient):
    # Assert initial conditions
    assert await plc.get_object_value("DQ0") == False # Tank is not filling
    assert await plc.get_object_value("DQ1") == False # Tank is not discharging
    assert await plc.get_object_value("DQ2") == False # Liquid is not heating
    
    # Simulate pressing the START button
    await plc.set_object_pulse("DI0") # Press START button
    await asyncio.sleep(1) # Waiting for transition into next step
    
    # Assert actuations after pressing START button
    assert await plc.get_object_value("DQ0") == True # Tank is filling
    assert await plc.get_object_value("DQ1") == False # Tank is not discharging
    assert await plc.get_object_value("DQ2") == False # Liquid is not heating

# Test low level has been reached
# @pytest.mark.asyncio
# async def test_prefilling_ready(plc: PLCClient):
#     # Simulate low level reached
#     pass
# Test RUN button pressed


# Test high level has been reached


# Test setpoint has been reached


# Test low level has been reached


# Stop button


# Add more test cases if needed
