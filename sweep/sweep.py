from ast import Pass
import dataclasses
import functools
import os
import socket
import inspect
import signal
import time
import datetime
from typing import Callable, Dict, List, Union
import numpy as np

from IPython import display, get_ipython

from . import db
from . import plot


BASEDIR = None
def set_basedir(path):
    global BASEDIR
    BASEDIR = path

def _sec_to_str(d):
    h, m, s = int(d/3600), int(d/60) % 60, int(d) % 60
    return f'{h}h {m}m {s}s'


@dataclasses.dataclass(repr=False)
class SweepResult:
    basedir:  str
    id:       int
    metadata: Dict
    datapath: str


def _interruptible(func):
    # We don't want to allow interrupts while communicating with
    # instruments. This checks for interrupts after measuring.
    # TODO: Allow interrupting the time.sleep() somehow, and potentially
    #       also the param(setpoint) if possible.
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args[0].interrupt_requested = False
        def handler(signum, frame):
            args[0].interrupt_requested = True
        old_handler = signal.signal(signal.SIGINT, handler)
        result = func(*args, **kwargs)
        signal.signal(signal.SIGINT, old_handler)
        return result
    return wrapper


class Station:
    '''A Station is a collection of parameters that can be measured.

    You can do 0D (measure), 1D (sweep), and 2D (megasweep) sweeps, and you can
    measure over time with watch.
    '''

    def __init__(self, basedir: str=None, verbose: bool=True):
        '''Create a Station.'''
        global BASEDIR
        if basedir is not None:
            self._basedir: str = basedir
        elif BASEDIR is not None:
            self._basedir: str = BASEDIR
        else:
            self._basedir: str = os.getcwd()

        self._verbose: bool = verbose
        self._params: List = []
        self._traces: List = []
        self._trace_cols: List = []
        self._traces_points: List = []
        self._plotter = plot.Plotter()
        self._notes = ""
        self._calling_file_path = os.path.join(os.getcwd(), os.path.splitext(os.path.basename(os.getcwd()))[0] + ".ipynb")

    def _measure(self) -> List[float]:
        return [p() / gain for p, gain in self._params]

    def _col_names(self) -> List[str]:
        if not self._traces:
            return [p.full_name for p, _ in self._params]
        elif self._traces:
            return [p.full_name for p, _ in self._params] + self._trace_cols

    def follow_param(self, param, gain: float=1.0):
        self._params.append((param, gain))
        return self
    
    def follow_trace(self, trace, gain: float=1.0):
        self._traces.append((trace, gain))
        trac_nam = trace._trace_name
        chan_name = trace._channel_name
        self._trace_cols.append(f'znle.{chan_name.lower()}.{trac_nam.lower()}_i')
        self._trace_cols.append(f'znle.{chan_name.lower()}.{trac_nam.lower()}_q')
        self._trace_cols.append(f'znle.{chan_name.lower()}.{trac_nam.lower()}')
        return self
    
    def add_notes(self, note: str):
        self._notes = note
        return self

    fp = follow_param

    def _print(self, msg):
        if self._verbose:
            print(msg)

    def plot(self, x, y, z=None):
        self._plotter.plot(x, y, z)

    def reset_plots(self):
        self._plotter.reset_plots()

    def measure(self):
        with db.Writer(self._basedir) as w:
            w.metadata['type'] = '0D'
            w.metadata['columns'] = ['time'] + self._col_names()
            t = time.time()
            w.metadata['time'] = t
            w.add_point([t] + self._measure())
        self._print(f'Data saved in {w.datapath}')
        return SweepResult(self._basedir, w.id, w.metadata, w.datapath)

    @_interruptible
    def watch(self, delay: float=0.0, max_duration=None):
        with db.Writer(self._basedir) as w, self._plotter as p:
            self._print(f'Starting run with ID {w.id}')
            w.metadata['type'] = '1D'
            w.metadata['delay'] = delay
            w.metadata['max_duration'] = max_duration
            w.metadata['columns'] = ['time'] + self._col_names()
            w.metadata['interrupted'] = False
            w.metadata['start_time'] = time.time()
            p.set_cols(w.metadata['columns'])
            t_start = time.monotonic() # Can't go backwards!
            while max_duration is None or time.monotonic() - t_start < max_duration:
                time.sleep(delay)
                data = [time.time()] + self._measure()
                w.add_point(data)
                p.add_point(data)
                if self.interrupt_requested:
                    w.metadata['interrupted'] = True
                    break
            w.metadata['end_time'] = time.time()
            image = p.send_image()
            if image is not None:
                w.add_blob('plot.png', image)
                display.display(display.Image(data=image, format='png'))
        duration = w.metadata['end_time'] - w.metadata['start_time']
        self._print(f'Completed in {_sec_to_str(duration)}')
        self._print(f'Data saved in {w.datapath}')

        return SweepResult(self._basedir, w.id, w.metadata, w.datapath)
                

    @_interruptible
    def sweep(self, param, setpoints, delay: float=0.0):
        with db.Writer(self._basedir) as w, self._plotter as p:
            self._print(f'Starting run with ID {w.id}')
            self._print(f'Minimum duration {_sec_to_str(len(setpoints) * delay)}')

            instruments_used = []
            param_indices = []
            for i in range(len(self._params)):
                instrument = str(self._params[i][0].instrument)
                if instrument not in instruments_used:
                    instruments_used.append(instrument)
                    param_indices.append(i)
            
            if self._notes != "":
                w.metadata['notes'] = self._notes
            
            w.metadata['computer used'] = socket.gethostname()
         
            w.metadata['measurement code ran from file'] = self._calling_file_path
            w.metadata['instruments used'] = instruments_used
            w.metadata['type'] = '1D'
            w.metadata['delay'] = delay
            w.metadata['param'] = param.full_name
            w.metadata['columns'] = ['time', param.full_name] + self._col_names()
            
            for i in range(len(instruments_used)):
                instrument_name = instruments_used[i]
                if "ZM2376" in instrument_name:
                    instrument = self._params[param_indices[i]][0].instrument
                    calibrations = [f"Short Correction State: {instrument.short_correction_state.get()}", 
                                    f"Open Correction State: {instrument.open_correction_state.get()}", 
                                    f"Load Correction State: {instrument.load_correction_state.get()}"]
                    w.metadata[f"calibrations ({instrument_name})"] = calibrations
                    variables = [f"Primary Parameter: {instrument.primary_var.get().strip()}",
                                 f"Secondar Parameter: {instrument.secondary_var.get().strip()}"]
                    w.metadata[f'variables ({instrument_name})'] = variables

                if "SR" in instrument_name:
                    instrument = self._params[param_indices[i]][0].instrument
                    w.metadata[f'frequency ({instrument_name})'] = instrument.frequency.get()
                    w.metadata[f'sine out amplitude ({instrument_name})'] = instrument.amplitude.get()

            w.metadata['setpoints'] = list(setpoints)
            w.metadata['interrupted'] = False
            w.metadata['start_time'] = time.time()
            w.metadata['human_readable start time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            p.set_cols(w.metadata['columns'])

            for setpoint in setpoints:
                param(setpoint)
                time.sleep(delay) # TODO: Account for time spent in between?
                data = [time.time(), setpoint] + self._measure()
                w.add_point(data)
                p.add_point(data)
                if self.interrupt_requested:
                    w.metadata['interrupted'] = True
                    break

            w.metadata['end_time'] = time.time()
            w.metadata['human_readable end time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            duration = w.metadata['end_time'] - w.metadata['start_time']
            w.metadata['time taken'] = str(_sec_to_str(duration))
            image = p.send_image()
            if image is not None:
                w.add_blob('plot.png', image)
                display.display(display.Image(data=image, format='png'))

        self._print(f'Completed in {_sec_to_str(duration)}')
        self._print(f'Data saved in {w.datapath}')

        return SweepResult(self._basedir, w.id, w.metadata, w.datapath)

    @_interruptible
    def megasweep(self, slow_param, slow_v, fast_param, fast_v, slow_delay=0, fast_delay=0):
        with db.Writer(self._basedir) as w, self._plotter as p:
            self._print(f'Starting run with ID {w.id}')
            min_duration = len(slow_v) * len(fast_v) * fast_delay + len(slow_v) * slow_delay
            self._print(f'Minimum duration {_sec_to_str(min_duration)}')

            instruments_used = []
            param_indices = []
            for i in range(len(self._params)):
                instrument = str(self._params[i][0].instrument)
                if instrument not in instruments_used:
                    instruments_used.append(instrument)
                    param_indices.append(i)
            
            if self._notes != "":
                w.metadata['notes'] = self._notes
            
            w.metadata['computer used'] = socket.gethostname()
         
            w.metadata['measurement code ran from file'] = self._calling_file_path
            w.metadata['instruments used'] = instruments_used

            w.metadata['type'] = '2D'
            w.metadata['slow_delay'] = slow_delay
            w.metadata['fast_delay'] = fast_delay
            w.metadata['slow_param'] = slow_param.full_name
            w.metadata['fast_param'] = fast_param.full_name
            w.metadata['columns'] = ['time', slow_param.full_name, fast_param.full_name] + self._col_names()

            for i in range(len(instruments_used)):
                instrument_name = instruments_used[i]
                if "ZM2376" in instrument_name:
                    instrument = self._params[param_indices[i]][0].instrument
                    calibrations = [f"Short Correction State: {instrument.short_correction_state.get()}", 
                                    f"Open Correction State: {instrument.open_correction_state.get()}", 
                                    f"Load Correction State: {instrument.load_correction_state.get()}"]
                    w.metadata[f"calibrations ({instrument_name})"] = calibrations
                    variables = [f"Primary Parameter: {instrument.primary_var.get().strip()}",
                                 f"Secondar Parameter: {instrument.secondary_var.get().strip()}"]
                    w.metadata[f'variables ({instrument_name})'] = variables

                if "SR" in instrument_name:
                    instrument = self._params[param_indices[i]][0].instrument
                    w.metadata[f'frequency ({instrument_name})'] = instrument.frequency.get()
                    w.metadata[f'sine out amplitude ({instrument_name})'] = instrument.amplitude.get()

            w.metadata['slow_setpoints'] = list(slow_v)
            w.metadata['fast_setpoints'] = list(fast_v)
            w.metadata['interrupted'] = False
            w.metadata['start_time'] = time.time()
            w.metadata['human_readable start time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            p.set_cols(w.metadata['columns'])

            for i in range(len(slow_v)):
                ov = slow_v[i]
                slow_param(ov)
                time.sleep(slow_delay)
                for j in range(len(fast_v)):
                    iv = fast_v[j]
                    fast_param(iv)
                    time.sleep(fast_delay)
                    data = [time.time(), ov, iv] + self._measure()
                    w.add_point(data)
                    if j == 0:
                        p.add_point_to_new_line(data)
                    else:
                        p.add_point(data)
                    if self.interrupt_requested:
                        w.metadata['interrupted'] = True
                        break
                if self.interrupt_requested:
                    break

            w.metadata['end_time'] = time.time()
            w.metadata['human_readable end time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            duration = w.metadata['end_time'] - w.metadata['start_time']
            w.metadata['time taken'] = str(_sec_to_str(duration))
            image = p.send_image()
            if image is not None:
                w.add_blob('plot.png', image)
                display.display(display.Image(data=image, format='png'))

        self._print(f'Completed in {_sec_to_str(duration)}')
        self._print(f'Data saved in {w.datapath}')

        return SweepResult(self._basedir, w.id, w.metadata, w.datapath)

    @_interruptible
    def sweep_vna_1d(self, delay: float=0.0):
        with db.Writer(self._basedir) as w, self._plotter as p:
            instruments_used = []
            param_indices = []
            for i in range(len(self._params)):
                instrument = str(self._params[i][0].instrument)
                if instrument not in instruments_used:
                    instruments_used.append(instrument)
                    param_indices.append(i)

            fast_param = 'znle_frequency'
            fast_v = self._traces[0][0].root_instrument.params.get_freq_setpoints()

            trace_infos = {trace[0]._trace_name : trace[0]._s_param for trace in self._traces}

            self._print(f'Starting run with ID {w.id}')
            min_duration = len(trace_infos.keys()) * (1 + delay)
            self._print(f'Minimum duration {_sec_to_str(min_duration)}')
            
            if self._notes != "":
                w.metadata['notes'] = self._notes
            
            w.metadata['computer used'] = socket.gethostname()
         
            w.metadata['measurement code ran from file'] = self._calling_file_path
            w.metadata['instruments used'] = instruments_used

            w.metadata['type'] = '1D_VNA_Sweep'
            w.metadata['delay'] = delay
            w.metadata['trace_information'] = trace_infos
            w.metadata['columns'] = ['time', fast_param] + self._col_names()

            for i in range(len(instruments_used)):
                instrument_name = instruments_used[i]
                if "ZM2376" in instrument_name:
                    instrument = self._params[param_indices[i]][0].instrument
                    calibrations = [f"Short Correction State: {instrument.short_correction_state.get()}", 
                                    f"Open Correction State: {instrument.open_correction_state.get()}", 
                                    f"Load Correction State: {instrument.load_correction_state.get()}"]
                    w.metadata[f"calibrations ({instrument_name})"] = calibrations
                    variables = [f"Primary Parameter: {instrument.primary_var.get().strip()}",
                                 f"Secondar Parameter: {instrument.secondary_var.get().strip()}"]
                    w.metadata[f'variables ({instrument_name})'] = variables

                if "SR" in instrument_name:
                    instrument = self._params[param_indices[i]][0].instrument
                    w.metadata[f'frequency ({instrument_name})'] = instrument.frequency.get()
                    w.metadata[f'sine out amplitude ({instrument_name})'] = instrument.amplitude.get()

            w.metadata['znle_freq_setpoints'] = list(fast_v)
            w.metadata['interrupted'] = False
            w.metadata['start_time'] = time.time()
            w.metadata['human_readable start time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            p.set_cols(w.metadata['columns'])

            traces_data = []
            traces_name = []

            for trace in self._traces:
                gain = trace[1]
                trace = trace[0]
                trace.set_as_active()
                raw_data = trace.iq_trace.get()

                i_data, q_data = raw_data
                noises = [10 * np.log10(i ** 2 + q ** 2) for i, q in zip(i_data, q_data)]
                processed_data = [i_data, q_data, noises]
                processed_data = [point for point in zip(*processed_data)]
                
                traces_data.append(processed_data)
                traces_name.append(trace._trace_name)

                time.sleep(delay)

            traces_points = [a + b for a, b in zip(*traces_data)]
            
            self._traces_points = traces_points

            for j in range(len(traces_points)):

                point_data = traces_points[j]
                iv = fast_v[j]
                data = [time.time(), iv] + self._measure()
                data.extend(point_data)
                w.add_point(data)
                p.add_point(data)
                
                if self.interrupt_requested:
                    w.metadata['interrupted'] = True
                    break

            w.metadata['end_time'] = time.time()
            w.metadata['human_readable end time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            duration = w.metadata['end_time'] - w.metadata['start_time']
            w.metadata['time taken'] = str(_sec_to_str(duration))
            image = p.send_image()
            if image is not None:
                w.add_blob('plot.png', image)
                display.display(display.Image(data=image, format='png'))

        self._print(f'Completed in {_sec_to_str(duration)}')
        self._print(f'Data saved in {w.datapath}')

        return SweepResult(self._basedir, w.id, w.metadata, w.datapath)
    

    @_interruptible
    def sweep_vna_2d(self, slow_param, slow_v, slow_delay=0):
        with db.Writer(self._basedir) as w, self._plotter as p:
            instruments_used = []
            param_indices = []
            for i in range(len(self._params)):
                instrument = str(self._params[i][0].instrument)
                if instrument not in instruments_used:
                    instruments_used.append(instrument)
                    param_indices.append(i)

            fast_param = 'znle_frequency'
            fast_v = self._traces[0][0].root_instrument.params.get_freq_setpoints()
            fast_delay = 0

            trace_infos = {trace[0]._trace_name : trace[0]._s_param for trace in self._traces}

            self._print(f'Starting run with ID {w.id}')
            min_duration = len(slow_v) * len(fast_v) * fast_delay + len(slow_v) * slow_delay
            self._print(f'Minimum duration {_sec_to_str(min_duration)}')
            
            if self._notes != "":
                w.metadata['notes'] = self._notes
            
            w.metadata['computer used'] = socket.gethostname()
         
            w.metadata['measurement code ran from file'] = self._calling_file_path
            w.metadata['instruments used'] = instruments_used

            w.metadata['type'] = '2D_VNA_Sweep'
            w.metadata['slow_delay'] = slow_delay
            w.metadata['fast_delay'] = fast_delay
            w.metadata['slow_param'] = slow_param.full_name
            w.metadata['fast_param'] = fast_param
            w.metadata['trace_information'] = trace_infos
            w.metadata['columns'] = ['time', slow_param.full_name, fast_param] + self._col_names()

            for i in range(len(instruments_used)):
                instrument_name = instruments_used[i]
                if "ZM2376" in instrument_name:
                    instrument = self._params[param_indices[i]][0].instrument
                    calibrations = [f"Short Correction State: {instrument.short_correction_state.get()}", 
                                    f"Open Correction State: {instrument.open_correction_state.get()}", 
                                    f"Load Correction State: {instrument.load_correction_state.get()}"]
                    w.metadata[f"calibrations ({instrument_name})"] = calibrations
                    variables = [f"Primary Parameter: {instrument.primary_var.get().strip()}",
                                 f"Secondar Parameter: {instrument.secondary_var.get().strip()}"]
                    w.metadata[f'variables ({instrument_name})'] = variables

                if "SR" in instrument_name:
                    instrument = self._params[param_indices[i]][0].instrument
                    w.metadata[f'frequency ({instrument_name})'] = instrument.frequency.get()
                    w.metadata[f'sine out amplitude ({instrument_name})'] = instrument.amplitude.get()

            w.metadata['slow_setpoints'] = list(slow_v)
            w.metadata['fast_setpoints'] = list(fast_v)
            w.metadata['interrupted'] = False
            w.metadata['start_time'] = time.time()
            w.metadata['human_readable start time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            p.set_cols(w.metadata['columns'])

            for i in range(len(slow_v)):
                ov = slow_v[i]
                slow_param(ov)
                time.sleep(slow_delay)

                slow_measurement = self._measure()

                traces_data = []
                traces_name = []

                for trace in self._traces:
                    gain = trace[1]
                    trace = trace[0]
                    trace.set_as_active()
                    raw_data = trace.iq_trace.get()

                    i_data, q_data = raw_data
                    noises = [10 * np.log10(i ** 2 + q ** 2) for i, q in zip(i_data, q_data)]
                    processed_data = [i_data, q_data, noises]
                    processed_data = [point for point in zip(*processed_data)]
                    
                    traces_data.append(processed_data)
                    traces_name.append(trace._trace_name)

                traces_points = [a + b for a, b in zip(*traces_data)]
                
                self._traces_points = traces_points

                for j in range(len(traces_points)):

                    point_data = traces_points[j]
                    iv = fast_v[j]
                    data = [time.time(), ov, iv] + slow_measurement
                    data.extend(point_data)
                    w.add_point(data)
                    if j == 0:
                        p.add_point_to_new_line(data)
                    else:
                        p.add_point(data)
                    
                    if self.interrupt_requested:
                        w.metadata['interrupted'] = True
                        break
                if self.interrupt_requested:
                    break

            w.metadata['end_time'] = time.time()
            w.metadata['human_readable end time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            duration = w.metadata['end_time'] - w.metadata['start_time']
            w.metadata['time taken'] = str(_sec_to_str(duration))
            image = p.send_image()
            if image is not None:
                w.add_blob('plot.png', image)
                display.display(display.Image(data=image, format='png'))

        self._print(f'Completed in {_sec_to_str(duration)}')
        self._print(f'Data saved in {w.datapath}')

        return SweepResult(self._basedir, w.id, w.metadata, w.datapath)