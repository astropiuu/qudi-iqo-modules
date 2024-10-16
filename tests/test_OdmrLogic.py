# -*- coding: utf-8 -*-

"""
This file contains unit tests for the ODMR logic module.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-core/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

import os
import time
import math
import numpy as np
import coverage
import pytest

MODULE = 'odmr_logic'
BASE = 'logic'
CHANNELS = ('APD counts', 'Photodiode')
FIT_MODEL = 'Gaussian Dip'
TOLERANCE = 10 # tolerance for signal data range


def get_scanner(logic_instance):
    """
    Getter for scanner module for ODMR logic module.

    Parameters
    ----------
    logic_instance : Object
        ODMR logic_instance

    Returns
    -------
    Object
        Scanner module instance
    """
    return logic_instance._data_scanner()

def get_microwave(logic_instance):
    """
    Getter for microwave module instance for logic module.

    Parameters
    ----------
    logic_instance : Object
        logic module instance

    Returns
    -------
    Object
        microwave module instance
    """
    return logic_instance._microwave()

def get_odmr_range(length, scanner):
    """
    Simulate odmr scan data and return signal data.

    Parameters
    ----------
    length : int
        Length of scans
    scanner : object
        Scanner module instance

    Returns
    -------
    dict
        Dict of simulated data for all the channels
    """
    scanner.__simulate_odmr(length)
    data = scanner._FiniteSamplingInputDummy__simulated_samples
    signal_data_range = {channel: ( get_tolerance(min(data[channel]), bound = 'lower'), get_tolerance( max(data[channel]), bound='upper')  ) for channel in data}
    return signal_data_range

def get_tolerance(value, bound):
    """
    Upper and lower boundaries for range check.

    Parameters
    ----------
    value : float
        Input value
    bound : str
        lower or upper bound category

    Returns
    -------
    int
        the limit
    """
    return int(value + value * TOLERANCE/100) if bound == 'upper' else int(value - value * TOLERANCE/100)


#@pytest.fixture(scope='logic_instance')
def get_logic_module_instance(remote_instance):
    """
    Fixture that returns ODMR logic instance.

    Parameters
    ----------
    remote_instance : fixture
        Remote qudi instance
    """
    module_manager = remote_instance.module_manager
    odmr_gui = 'odmr_gui'
    odmr_logic = 'odmr_logic'
    module_manager.activate_module(odmr_gui)
    logic_instance = module_manager._modules[odmr_logic].instance
    return logic_instance

'''
@pytest.fixture(autouse=True)
def coverage_for_each_test(request):
    """
    Generate and save coverage report.

    Parameters
    ----------
    request : request
    """
    cov = coverage.Coverage()
    cov.start()
    yield
    cov.stop()
    test_dir =  f"coverage_{request.node.nodeid.replace('/', '_').replace(':', '_')}"
    os.makedirs(test_dir, exist_ok=True)
    cov.html_report(directory=test_dir)
    cov.save()
    print(f"Coverage report saved to {test_dir}")
'''

def test_start_odmr_scan(remote_instance):
    """
    Tests if the scan parameters are correctly generated and if the signal data is generated for the given runtime
    with appropriate values.

    Parameters
    ----------
    logic_instance : fixture
        Fixture for logic_instance of ODMR logic logic_instance
    scanner : fixture
        Fixture for connected logic_instance of Finite sampling input dummy for data scanning
    qtbot : fixture
        Fixture for qt support
    """
    logic_instance = get_logic_module_instance(remote_instance)
    scanner = get_scanner(logic_instance)
    logic_instance.runtime = 5
    freq_low, freq_high, freq_counts = list(map(int, logic_instance.frequency_ranges[0]))
    frequency_data = logic_instance.frequency_data
    assert len(frequency_data) == logic_instance.frequency_range_count
    for data_range in frequency_data:
        assert len(data_range) == freq_counts
        for freq_value in data_range:
            assert isinstance(freq_value, float)
            assert int(freq_value) in range(freq_low, freq_high+1)
    
    logic_instance.start_odmr_scan()
    run_time = int(logic_instance._run_time) 
    #with qtbot.waitSignals( [logic_instance._sigNextLine]*run_time, timeout = run_time*1500) as blockers:
    #    pass
    time.sleep(run_time)
    signal_data = logic_instance.signal_data
    assert len(signal_data) == len(scanner.active_channels)
    odmr_range = get_odmr_range(5, scanner)
    for channel in signal_data:
        for values in signal_data[channel]:
            assert len(values) == freq_counts
            for value in values:
                assert isinstance(value,float)
                assert not math.isnan(value)
                assert int(value) in range(*odmr_range[channel])
    #print(f'elspased sweeps {logic_instance._elapsed_sweeps}') 

'''

def test_do_fit(remote_instance):
    """
    Tests if the fitting of the generated signal data works by checking the values of the fit parameters are not nan.

    Parameters
    ----------
    remote_instance : fixture
        Fixture for instance of ODMR logic module
    """
    logic_instance = get_logic_module_instance(remote_instance)
    logic_instance.do_fit(FIT_MODEL, CHANNELS[0], 0)
    fit_results  = logic_instance.fit_results[CHANNELS[0]][0][1]
    dict_fit_result = logic_instance.fit_container.dict_result(fit_results)
    for key,values in dict_fit_result.items():
        if 'value' in values:
            assert not math.isnan(values['value'])

def test_save_odmr_data(remote_instance):
    """
    Tests whether new files were saved in the save dir after executing the save function. If a new file exists, the
    contents are checked against the actual signal data to ensure that the data is saved correctly.

    Parameters
    ----------
    logic_instance : fixture
        Fixture for logic_instance of ODMR logic logic_instance
    """
    logic_instance = get_logic_module_instance(remote_instance)

    save_dir = logic_instance.module_default_data_dir
    if os.path.exists(save_dir):
        saved_files = os.listdir(save_dir)
        saved_files = [os.path.join(save_dir, file) for file in saved_files]
        creation_times = np.array([os.path.getmtime(file) for file in saved_files])
        current_time = time.time()
        time_diffs =   current_time - creation_times
        assert(not any(time_diffs<5)) # no files should be created in the last 5 secs before saving
        
    logic_instance.save_odmr_data()
    
    saved_files = os.listdir(save_dir)
    saved_files = [os.path.join(save_dir, file) for file in saved_files]
    creation_times = np.array([os.path.getmtime(file) for file in saved_files])
    current_time = time.time()
    time_diffs = current_time - creation_times
    recent_saved_files = [saved_file for saved_file,time_diff in zip(saved_files, time_diffs) if time_diff<5]
    data_files = [recent_saved_file for recent_saved_file in recent_saved_files if os.path.splitext(recent_saved_file)[1] == '.dat']
    signal_data_file = [data_file for data_file in data_files if 'signal' in data_file][0]
    saved_signal_data = np.loadtxt(signal_data_file)
    from qudi.util.network import netobtain
    for i,channel in enumerate(CHANNELS):
        saved_channel_data = [saved_signal_row[i+1]  for saved_signal_row in saved_signal_data]
        actual_channel_data = netobtain(logic_instance.signal_data[channel][0])
        assert np.allclose(saved_channel_data, actual_channel_data)
'''