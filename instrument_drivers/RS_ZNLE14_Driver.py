import numpy as np
from qcodes import VisaInstrument, InstrumentChannel

class ZNLE14(VisaInstrument):
    """
    ZNLE14 VNA Instrument class.

    Parameters:
        name (str): Name of the instrument.
        address (str): VISA address of the instrument.
        **kwargs: Additional keyword arguments.

    Attributes:
        _channel_list (dict): Dictionary of available channels.

    Methods:
        reset(): Reset the instrument.
        _initialize_submodules(): Initialize submodules for channels, display, and parameters.
        get_all_traces(): Get all available traces.
        get_all_channels(): Get all available channels.
        create_new_channel(channel_num: int): Create a new channel.
        _get_all_trace_data_parser(raw_data: str): Parse raw trace data.
    """

    def __init__(self, name: str, address: str, **kwargs):
        """
        Initialize ZNLE14 VNA Instrument.

        Args:
            name (str): Name of the instrument.
            address (str): VISA address of the instrument.
            **kwargs: Additional keyword arguments.
        """
        
        super().__init__(name, address, terminator='\r\n', **kwargs)
        self.connect_message()
        
        self._initialize_submodules()
        
        self.add_parameter(
            "iq_trace_all_traces",
            get_cmd='calc:data:all? sdat',
            get_parser=self._get_all_trace_data_parser,
            label='IQ Trace for all Traces on Instrument'
        )
        
    def reset(self):
        """Reset the instrument."""
        self.write('*rst')
        self.submodules.clear()
        self._initialize_submodules()

    def _initialize_submodules(self):
        """Initialize submodules for channels, display, and parameters."""
        self._channel_list = self.get_all_channels()
        for channel_num in self._channel_list.keys():
            channel = ZNLE14Channel(parent=self, channel_num=channel_num)
            self.add_submodule(channel._channel_name.lower(), channel)
            all_traces = channel.get_all_traces_in_channel()
            for trace_num in all_traces.keys():
                channel.create_new_trace(trace_num=trace_num, pre_existing=True)
                
        display = ZNLE14Display(parent=self)
        self.add_submodule('display', display)
        
        params = ZNLEParams(parent=self)
        self.add_submodule('params', params)
        
    def get_all_traces(self):
        """Get all available traces."""
        traces = self.ask('conf:trac:cat?').strip()
        trace_nums = traces.split(',')[0::2]
        trace_names = traces.split(',')[1::2]
        traces = {num.strip("'") : name.strip("'") for num, name in zip(trace_nums, trace_names)}
        return traces
    
    def get_all_channels(self):
        """Get all available channels."""
        channels = self.ask('conf:chan:cat?').strip()
        channel_nums = channels.split(',')[0::2]
        channel_names = channels.split(',')[1::2]
        channels = {num.strip("'") : name.strip("'") for num, name in zip(channel_nums, channel_names)}
        return channels

    def create_new_channel(self, channel_num: int):
        """Create a new channel."""
        if str(channel_num) in list(self.get_all_channels().keys()):
            raise AttributeError("Channel with this number already exists.")
        else:
            channel = ZNLE14Channel(parent=self, channel_num=channel_num)
            self.add_submodule(channel._channel_name.lower(), channel)
        
        self._channel_list = self.get_all_channels()
        
    def _get_all_trace_data_parser(self, raw_data: str):
        """Parse raw trace data."""
        data = raw_data.strip().split(',')
        data = [float(point) for point in data]
        i_all = data[0::2]
        q_all = data[1::2]
        
        num_swe_points = self.params.sweep_points.get()
        
        i_s = [i_all[i:i + num_swe_points] for i in range(0, len(i_all), num_swe_points)]
        q_s = [q_all[i:i + num_swe_points] for i in range(0, len(q_all), num_swe_points)]
        
        return i_s, q_s
    
class ZNLE14Channel(InstrumentChannel):
    """
    ZNLE14 Channel class.

    Parameters:
        parent (ZNLE14): Parent instrument.
        channel_num (int): Channel number.

    Attributes:
        _channel_num (int): Channel number.
        _channel_name (str): Channel name.

    Methods:
        create_new_trace(trace_num: int, s_param: Optional[str] = None, pre_existing: Optional[bool] = False): Create a new trace.
        get_all_traces_in_channel(): Get all traces in the channel.
        _get_all_trace_data_parser(raw_data: str): Parse raw trace data.
    """
    
    def __init__(self, parent: ZNLE14, channel_num: int) -> None:
        """
        Initialize ZNLE14 Channel.

        Args:
            parent (ZNLE14): Parent instrument.
            channel_num (int): Channel number.
        """
        
        self._channel_num = channel_num
        self._channel_name = f"Ch{self._channel_num}"
        
        super().__init__(parent, self._channel_name)
        
        self.add_parameter(
            "iq_trace_all_channeltraces",
            get_cmd='calc1:data:chan:dall? sdat',
            get_parser = self._get_all_trace_data_parser,
            label='IQ Trace for all Traces in Channels'
        )
                
    def create_new_trace(self, trace_num: int, s_param: str = None, pre_existing: bool = False):
        """Create a new trace."""
        if pre_existing:
            trace = ZNLE14ChannelTrace(self, trace_num, 'S21')
            self.add_submodule(trace._trace_name.lower(), trace)
        else:
            if str(trace_num) in list(self._parent.get_all_traces().keys()):
                raise AttributeError("Trace with this number already exists.")
            else:
                trace_name = f"Trc{trace_num}"
                self._parent.write(f'calc{self._channel_num}:par:sdef "{trace_name}", "{s_param}"')
                trace = ZNLE14ChannelTrace(self, trace_num, s_param)
                self.add_submodule(trace._trace_name.lower(), trace)
                
        self._channel_traces = self.get_all_traces_in_channel()
                        
    def get_all_traces_in_channel(self):
        """Get all traces in the channel."""
        traces = self._parent.ask(f'conf:chan{self._channel_num}:trac:cat?').strip()
        trace_nums = traces.split(',')[0::2]
        trace_names = traces.split(',')[1::2]
        traces = {num.strip("'") : name.strip("'") for num, name in zip(trace_nums, trace_names)}
        return traces
    
    def _get_all_trace_data_parser(self, raw_data: str):
        """Parse raw trace data."""
        data = raw_data.strip().split(',')
        data = [float(point) for point in data]
        i_all = data[0::2]
        q_all = data[1::2]
        
        num_swe_points = self._parent.params.sweep_points.get()
        
        i_s = [i_all[i:i + num_swe_points] for i in range(0, len(i_all), num_swe_points)]
        q_s = [q_all[i:i + num_swe_points] for i in range(0, len(q_all), num_swe_points)]
        
        return i_s, q_s
    
class ZNLE14ChannelTrace(InstrumentChannel):
    """
    ZNLE14 Channel Trace class.

    Parameters:
        parent (ZNLE14Channel): Parent channel.
        trace_num (int): Trace number.
        s_param (Optional[str]): S-parameter name.

    Attributes:
        _trace_name (str): Trace name.
        _s_param (Optional[str]): S-parameter name.
        _channel_name (str): Channel name.

    Methods:
        set_as_active(): Set the trace as active.
        delete_trace(): Delete the trace.
        _iq_trace_parser(raw_data: str): Parse IQ trace data.
        _iq_point_parser(raw_data: str): Parse IQ point data.
    """
    
    def __init__(self, parent: ZNLE14Channel, trace_num: int, s_param: str = None) -> None:
        """
        Initialize ZNLE14 Channel Trace.

        Args:
            parent (ZNLE14Channel): Parent channel.
            trace_num (int): Trace number.
            s_param (Optional[str]): S-parameter name.
        """

        self._trace_name = f"Trc{trace_num}"
        self._s_param = s_param

        super().__init__(parent, self._trace_name.lower())
        
        self._channel_name = self._parent._channel_name
        
        self.add_parameter(
            "iq_trace",
            get_cmd=f"calc:data:trac? '{self._trace_name}', sdat",
            get_parser = self._iq_trace_parser,
            label='Real and Imaginary Trace Data'
        )
        
        self.add_parameter(
            "iq_points",
            get_cmd=f"calc:data:trac? '{self._trace_name}', sdat",
            get_parser = self._iq_point_parser,
            label='Real and Imaginary Point Data'
        )
        
    def set_as_active(self):
        """Set the trace as active."""
        self._parent._parent.write(f'calc{self._parent._channel_num}:par:sel {self._trace_name}')
        
    def delete_trace(self):
        """Delete the trace."""
        self._parent._parent.write(f":calc:par:del '{self._trace_name}'")
        self._parent.submodules.pop(self._label)

    def _iq_trace_parser(self, raw_data: str):
        """Parse IQ trace data."""
        data = raw_data.strip().split(',')
        data = [float(point) for point in data]
        i = data[0::2]
        q = data[1::2]
        
        return i, q
    
    def _iq_point_parser(self, raw_data: str):
        """Parse IQ point data."""
        data = raw_data.strip().split(',')
        data = [float(point) for point in data]
        i = data[0::2]
        q = data[1::2]
        
        return np.mean(i), np.mean(q)

class ZNLE14Display(InstrumentChannel):
    """
    ZNLE14 Display class.

    Parameters:
        parent (ZNLE14Channel): Parent channel.

    Methods:
        get_all_windows(): Get all available windows.
        create_a_new_disp_window(window_num: Optional[int] = None): Create a new display window.
        add_trace_to_new_window(trace: ZNLE14ChannelTrace, window_num: Optional[int] = None): Add a trace to a new window.
        autoscale_on_all_windows(): Autoscale on all windows.
    """
    
    def __init__(self, parent: ZNLE14Channel) -> None:
        """
        Initialize ZNLE14 Display.

        Args:
            parent (ZNLE14Channel): Parent channel.
        """

        super().__init__(parent, 'display')
        
        self._windows_dict = self.get_all_windows()
        for window_num in list(self._windows_dict.keys()):
            window = ZNLE14DisplayWindow(parent=self, window_num=window_num)
            self.add_submodule(window._window_name, window)
        
    def get_all_windows(self):
        """Get all available windows."""
        windows = self._parent.ask('disp:wind:cat?').strip()
        window_nums = windows.split(',')[0::2]
        window_names = windows.split(',')[1::2]
        windows = {num.strip("'") : name.strip("'") for num, name in zip(window_nums, window_names)}
        return windows
    
    def create_a_new_disp_window(self, window_num: int = None):
        """Create a new display window."""
        if window_num is None:
            window_nums = list(self._windows_dict.keys())
            window_nums = [int(x) for x in window_nums]
            window_num = np.max(window_nums) + 1
            
        self._parent.write(f'disp:wind{window_num}:stat on')
        
        window = ZNLE14DisplayWindow(parent=self, window_num=window_num)
        self.add_submodule(window._window_name, window)
        
        self._windows_dict = self.get_all_windows()
        
    def add_trace_to_new_window(self, trace: ZNLE14ChannelTrace, window_num: int = None):
        """Add a trace to a new window."""
        self.create_a_new_disp_window(window_num=window_num)
        self._parent.write(f'disp:wind{window_num}:trac:efe "{trace._trace_name}"')
        
        window = ZNLE14DisplayWindow(parent=self, window_num=window_num)
        self.add_submodule(window._window_name, window)
        
        self._windows_dict = self.get_all_windows()
        
    def autoscale_on_all_windows(self):
        """Autoscale on all windows."""
        window_nums = self._windows_dict.keys()
        window_nums = [int(num) for num in window_nums]
        for window_num in window_nums:
            self.write(f'disp:wind{window_num}:trac:y:auto once')

class ZNLE14DisplayWindow(InstrumentChannel):
    """
    ZNLE14 Display Window class.

    Parameters:
        parent (ZNLE14Display): Parent display.
        window_num (int): Window number.

    Methods:
        add_trace(trace: ZNLE14ChannelTrace): Add a trace to the window.
        autoscale_on(): Autoscale on the window.
    """
    
    def __init__(self, parent: ZNLE14Display, window_num: int) -> None:
        """
        Initialize ZNLE14 Display Window.

        Args:
            parent (ZNLE14Display): Parent display.
            window_num (int): Window number.
        """
        
        self._window_num = window_num
        self._window_name = f'win{self._window_num}'

        super().__init__(parent, self._window_name)
        
    def add_trace(self, trace: ZNLE14ChannelTrace):
        """Add a trace to the window."""
        self._parent.write(f'disp:wind{self._window_num}:trac:efe "{trace._trace_name}"')
        
    def autoscale_on(self):
        """Autoscale on the window."""
        self.write(f'disp:wind{self._window_num}:trac:y:auto once')

class ZNLEParams(InstrumentChannel):
    """
    ZNLE14 Parameters class.

    Parameters:
        parent (ZNLE14Display): Parent display.

    Methods:
        get_freq_setpoints(): Get frequency setpoints.
        _sweep_type_parser(sweep_type: str): Parse sweep type.
        _get_state_parser(state: str): Parse state.
        _set_state_parser(state): Set state.
    """
    
    def __init__(self, parent: ZNLE14Display) -> None:
        """
        Initialize ZNLE14 Parameters.

        Args:
            parent (ZNLE14Display): Parent display.
        """

        super().__init__(parent, 'params')
        
        self._sweep_types = {'LIN' : 'Linear', 'LOG' : 'Logarithmic', 'CW' : 'Time Sweep'}
        
        self.add_parameter(
            "freq_center",
            get_cmd='freq:cent?',
            get_parser = float,
            set_cmd='freq:cent {}',
            set_parser = float,
            label='Center of Frequency Range'
        )
                
        self.add_parameter(
            "freq_span",
            get_cmd='freq:span?',
            get_parser = float,
            set_cmd='freq:span {}',
            set_parser = float,
            label='Span of Frequency Range'       
        )
        
        self.add_parameter(
            "freq_start",
            get_cmd='freq:star?',
            get_parser = float,
            set_cmd='freq:star {}',
            set_parser = float,
            label='Start of Frequency Range'
        )
        
        self.add_parameter(
            "freq_stop",
            get_cmd='freq:stop?',
            get_parser = float,
            set_cmd='freq:stop {}',
            set_parser = float,
            label='Stop of Frequency Range'
        )
        
        self.add_parameter(
            "sweep_points",
            get_cmd='swe:poin?',
            get_parser = int,
            set_cmd='swe:point {}',
            set_parser = int,
            label='Number of Points in a Sweep'
        )
        
        self.add_parameter(
            "sweep_type",
            get_cmd='swe:type?',
            get_parser = str,
            set_cmd='swe:type {}',
            set_parser = self._sweep_type_parser,
            label='Type of the Sweep'
        )
        
        self.add_parameter(
            "aver_state",
            get_cmd='aver:stat?',
            get_parser = self._get_state_parser,
            set_cmd='aver:stat {}',
            set_parser = self._set_state_parser,
            label='Averaging On or Off'
        )
        
        self.add_parameter(
            "aver_count",
            get_cmd='aver:coun?',
            get_parser = int,
            set_cmd='aver:coun {}',
            set_parser = int,
            label='Averaging Counts'
        )
        
        self.add_parameter(
            "bandwidth",
            get_cmd='band?',
            get_parser = float,
            set_cmd='band {}',
            set_parser = float,
            label='Analyzer IF Bandwidth'
        )
        
        self.add_parameter(
            "power",
            get_cmd=':sour:pow?',
            get_parser = float,
            set_cmd=':sour:pow {}',
            set_parser = float,
            label='Source Power'
        )
        
    def get_freq_setpoints(self):
        """Get frequency setpoints."""
        start = self.freq_start.get()
        stop = self.freq_stop.get()
        num_points = self.sweep_points.get()
        sweep_type = self.sweep_type.get().strip()
        
        if sweep_type.lower() == 'lin':
            setpoints = np.linspace(start, stop, num_points)
        elif sweep_type.lower() == 'log':
            setpoints = np.logspace(np.log10(start), np.log10(stop), num_points)
            
        return setpoints
        
    def _sweep_type_parser(self, sweep_type):
        """Parse sweep type."""
        if sweep_type not in self._sweep_types:
            raise AttributeError(f'Sweep type must be in {list(self._sweep_types.keys())}. Check instrument._sweep_types.')
        else:
            return sweep_type
            
    def _get_state_parser(self, state):
        """Parse state."""
        if state == '0':
            return True
        else:
            return False
        
    def _set_state_parser(self, state):
        """Set state."""
        if state:
            return '1'
        else:
            return '0'