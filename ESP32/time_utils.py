# time_utils.py
import time
from machine import Timer
from hardware_utils import log_message

system_start_time = time.ticks_ms()

def get_uptime() -> str:
    """Get system uptime as formatted string."""
    uptime_ms = time.ticks_diff(time.ticks_ms(), system_start_time)
    seconds = uptime_ms // 1000
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m {seconds % 60}s"

def get_uptime_ms() -> int:
    """Get system uptime in milliseconds."""
    return time.ticks_diff(time.ticks_ms(), system_start_time)

def measure_execution_time(func, *args, **kwargs) -> tuple:
    """Measure function execution time."""
    start_time = time.ticks_ms()
    result = func(*args, **kwargs)
    end_time = time.ticks_ms()
    execution_time = time.ticks_diff(end_time, start_time)
    return result, execution_time

def create_timer(period_ms: int, callback, mode: int = Timer.PERIODIC) -> Timer:
    """Create a hardware timer."""
    try:
        timer = Timer(-1)
        timer.init(period=period_ms, mode=mode, callback=callback)
        return timer
    except Exception as e:
        log_message("ERROR", f"Timer creation failed: {e}")
        return None

def stop_timer(timer: Timer) -> None:
    """Stop a hardware timer."""
    try:
        if timer:
            timer.deinit()
    except Exception as e:
        log_message("ERROR", f"Timer stop failed: {e}")