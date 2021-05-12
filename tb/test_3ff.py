#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File              : test_afifo.py
# License           : MIT license <Check LICENSE>
# Author            : Anderson Ignacio da Silva (aignacio) <anderson@aignacio.com>
# Date              : 12.05.2021
# Last Modified Date: 12.05.2021
# Last Modified By  : Anderson Ignacio da Silva (aignacio) <anderson@aignacio.com>
import random
import cocotb
import os
import logging
import pytest

from logging.handlers import RotatingFileHandler
from cocotb.log import SimColourLogFormatter, SimLog, SimTimeContextFilter
from cocotb.regression import TestFactory
from cocotb_test.simulator import run
from cocotb.regression import TestFactory
from cocotb.clock import Clock
from cocotb_bus.drivers import Driver
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer
from collections import namedtuple

CLK_100MHz = (10, "ns")
CLK_50MHz  = (20, "ns")
RST_CYCLES = 2
WAIT_CYCLES = 2

async def setup_dut(dut, clk_mode):
    dut._log.info("Configuring clocks... -- %d", clk_mode)
    if clk_mode == 0:
        dut._log.info("50MHz clk")
        cocotb.fork(Clock(dut.clk_sync, *CLK_50MHz).start())
    else:
        dut._log.info("100MHz - clk")
        cocotb.fork(Clock(dut.clk_sync, *CLK_100MHz).start())

async def reset_dut(dut):
    dut.arst_master.setimmediatevalue(0)
    dut._log.info("Reseting DUT")
    dut.arst_master <= 1
    await ClockCycles(dut.clk_sync, RST_CYCLES)
    dut.arst_master.setimmediatevalue(0)

def randomly_switch_config():
    return random.randint(0, 1)

async def run_test(dut, config_clock):
    MAX_WIDTH = int(os.environ['PARAM_DATA_WIDTH'])
    TEST_RUNS = int(os.environ['TEST_RUNS'])
    await setup_dut(dut, config_clock)
    await reset_dut(dut)

    for i in range(TEST_RUNS):
        data = 2**random.randint(0,MAX_WIDTH)-1
        dut.async_i.setimmediatevalue(data)
        await ClockCycles(dut.clk_sync, 3)
        print(f"Expected ["+str(data)+"], dut.sync_o.value ["+str(dut.sync_o.value)+"]")
        assert data == dut.sync_o.value, "Unexpected 3FF behavior!"

if cocotb.SIM_NAME:
    factory = TestFactory(run_test)
    factory.add_option('config_clock', [0, 1])
    factory.generate_tests()

@pytest.mark.parametrize("width",[1,2,4,8])
def test_3ff(width):
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    rtl_dir   = tests_dir
    dut = "cdc_3ff_sync"
    module = os.path.splitext(os.path.basename(__file__))[0]
    toplevel = dut
    verilog_sources = [
        os.path.join(rtl_dir, f"../src/{dut}.sv"),
    ]
    parameters = {}
    parameters['DATA_WIDTH'] = width

    extra_env = {f'PARAM_{k}': str(v) for k, v in parameters.items()}
    extra_env['TEST_RUNS'] = str(random.randint(5,10))
    extra_env['COCOTB_HDL_TIMEUNIT'] = "1ns"
    extra_env['COCOTB_HDL_TIMEPRECISION'] = "1ns"

    sim_build = os.path.join(tests_dir, "../run_dir/sim_build_3ff_width_"+"_".join(("{}={}".format(*i) for i in parameters.items())))

    run(
        python_search=[tests_dir],
        verilog_sources=verilog_sources,
        toplevel=toplevel,
        module=module,
        parameters=parameters,
        sim_build=sim_build,
        extra_env=extra_env,
        extra_args=["--trace-fst","--trace-structs"]
        #extra_args=extra_args
    )
