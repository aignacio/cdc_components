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

class AFIFODriver():
    def __init__(self, signals, debug=False, slots=0, width=0):
        level         = logging.DEBUG if debug else logging.WARNING
        self.log      = SimLog("afifo.log")
        file_handler  = RotatingFileHandler("sim.log", maxBytes=(5 * 1024 * 1024), backupCount=2, mode='w')
        file_handler.setFormatter(SimColourLogFormatter())
        self.log.addHandler(file_handler)
        self.log.addFilter(SimTimeContextFilter())
        self.log.setLevel(level)
        self.log.info("SEED ======> %s",str(cocotb.RANDOM_SEED))

        self.clk_wr   = signals.clk_wr
        self.valid_wr = signals.wr_en_i
        self.data_wr  = signals.wr_data_i
        self.ready_wr = signals.wr_full_o
        self.clk_rd   = signals.clk_rd
        self.valid_rd = signals.rd_empty_o
        self.data_rd  = signals.rd_data_o
        self.ready_rd = signals.rd_en_i
        self.valid_wr <= 0
        self.ready_rd <= 0
        self.log.setLevel(level)

    async def write(self, data, sync=True, **kwargs):
        self.log.info("[AFIFO driver] write => %x"%data)
        while True:
            await FallingEdge(self.clk_wr)
            self.valid_wr <= 1
            self.data_wr  <= data
            await RisingEdge(self.clk_wr)
            if self.ready_wr == 0:
                break
            elif kwargs["exit_full"] == True:
                return "FULL"
        self.valid_wr <= 0
        return 0

    async def read(self, sync=True, **kwargs):
        while True:
            await FallingEdge(self.clk_rd)
            if self.valid_rd == 0:
                data = self.data_rd.value # We capture before we incr. rd ptr
                self.ready_rd <= 1
                await RisingEdge(self.clk_rd)
                break
            elif kwargs["exit_empty"] == True:
                return "EMPTY"
        self.log.info("[AFIFO-driver] read => %x"%data)
        self.ready_rd <= 0
        return data

async def setup_dut(dut, clk_mode):
    dut._log.info("Configuring clocks... -- %d", clk_mode)
    if clk_mode == 0:
        dut._log.info("50MHz - wr clk / 100MHz - rd clk")
        cocotb.fork(Clock(dut.clk_wr, *CLK_50MHz).start())
        cocotb.fork(Clock(dut.clk_rd, *CLK_100MHz).start())
    else:
        dut._log.info("50MHz - rd clk / 100MHz - wr clk")
        cocotb.fork(Clock(dut.clk_rd, *CLK_50MHz).start())
        cocotb.fork(Clock(dut.clk_wr, *CLK_100MHz).start())

async def reset_dut(dut):
    dut.arst_wr.setimmediatevalue(0)
    dut.arst_rd.setimmediatevalue(0)
    dut._log.info("Reseting DUT")
    dut.arst_wr <= 1
    dut.arst_rd <= 1
    await ClockCycles(dut.clk_wr, RST_CYCLES)
    dut.arst_wr <= 1
    dut.arst_rd <= 1
    await ClockCycles(dut.clk_rd, RST_CYCLES)
    dut.arst_rd <= 0
    dut.arst_wr <= 0

def randomly_switch_config():
    return random.randint(0, 1)

async def run_test(dut, config_clock):
    logging.basicConfig(filename='sim.log', encoding='utf-8', level=logging.DEBUG)
    MAX_SLOTS_FIFO = int(os.environ['PARAM_SLOTS'])
    MAX_WIDTH_FIFO = int(os.environ['PARAM_WIDTH'])
    TEST_RUNS = int(os.environ['TEST_RUNS'])
    await setup_dut(dut, config_clock)
    await reset_dut(dut)
    ff_driver = AFIFODriver(signals=dut,debug=True,slots=MAX_SLOTS_FIFO,width=MAX_WIDTH_FIFO)
    for i in range(TEST_RUNS):
        samples = [random.randint(0,(2**MAX_WIDTH_FIFO)-1) for i in range(random.randint(0,MAX_SLOTS_FIFO))]
        for i in samples:
            await ff_driver.write(i,exit_full=False)
        for i in samples:
            assert (read_value := await ff_driver.read(exit_empty=False)) == i, "%d != %d" % (read_value, i)
    # Testing FIFO full flag
    await reset_dut(dut)
    samples = [random.randint(0,(2**MAX_WIDTH_FIFO)-1) for i in range(MAX_SLOTS_FIFO)]
    for i in samples:
            await ff_driver.write(i,exit_full=False)
    assert (value := await ff_driver.write(samples[0],exit_full=True)) == "FULL", "AFIFO not signaling full correctly"
    # Testing FIFO empty flag
    await reset_dut(dut)
    assert (value := await ff_driver.read(exit_empty=True)) == "EMPTY", "AFIFO not signaling empty correctly"

if cocotb.SIM_NAME:
    factory = TestFactory(run_test)
    factory.add_option('config_clock', [0, 1])
    factory.generate_tests()

@pytest.mark.parametrize("slots",[2,4,8,16,32,64,128])
def test_fifo_async(slots):
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    rtl_dir   = tests_dir
    dut = "cdc_async_fifo"
    module = os.path.splitext(os.path.basename(__file__))[0]
    toplevel = dut
    verilog_sources = [
        os.path.join(rtl_dir, f"../src/{dut}.sv"),
    ]
    parameters = {}
    parameters['SLOTS'] = slots
    parameters['WIDTH'] = 2**random.randint(2,8)

    extra_env = {f'PARAM_{k}': str(v) for k, v in parameters.items()}
    extra_env['TEST_RUNS'] = str(random.randint(2,10))
    extra_env['COCOTB_HDL_TIMEUNIT'] = "1ns"
    extra_env['COCOTB_HDL_TIMEPRECISION'] = "1ns"

    sim_build = os.path.join(tests_dir, "../run_dir/sim_build_afifo_"+"_".join(("{}={}".format(*i) for i in parameters.items())))

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
