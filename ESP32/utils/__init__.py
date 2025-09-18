from .time_utils import *
from .io_utils import *
from .math_utils import *
from .json_utils import *
from .system_utils import *
from .hardware_utils import *

def create_status_dict() -> dict:
    return {
        'uptime': get_uptime(),
        'uptime_ms': get_uptime_ms(),
        'free_memory': format_bytes(get_free_memory()),
        'cpu_freq': get_cpu_freq(),
        'temperature': get_temperature(),
        'hardware_ok': is_hardware_initialized(),
        'timestamp': time.ticks_ms()
    }