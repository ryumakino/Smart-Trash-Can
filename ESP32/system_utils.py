import time
from hardware_utils import log_message

def generate_id() -> str:
    return str(time.ticks_ms())

def deep_sleep(duration_ms: int) -> None:
    try:
        import machine
        machine.deepsleep(duration_ms * 1000)
    except Exception as e:
        log_message("ERROR", f"Deep sleep failed: {e}")

def soft_reset() -> None:
    try:
        import machine
        machine.reset()
    except Exception as e:
        log_message("ERROR", f"Soft reset failed: {e}")

def validate_ip(ip: str) -> bool:
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        return True
    except:
        return False

def get_network_info() -> dict:
    """Retorna informações da rede"""
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
        if wlan.isconnected():
            ip, subnet, gateway, dns = wlan.ifconfig()
            return {
                'ip': ip,
                'subnet': subnet,
                'gateway': gateway,
                'dns': dns,
                'mac': ':'.join(['%02x' % i for i in wlan.config('mac')]),
                'hostname': network.hostname() if hasattr(network, 'hostname') else 'esp32',
                'connected': True
            }
    except:
        pass
    return {
        'ip': '0.0.0.0',
        'subnet': '0.0.0.0',
        'gateway': '0.0.0.0',
        'dns': '0.0.0.0',
        'mac': 'unknown',
        'hostname': 'esp32',
        'connected': False
    }

from time_utils import get_uptime_ms
from config import STATUS_UPDATE_INTERVAL_MS
from system_utils import log_component_status

def print_system_status(sensor, system_ready, servo_controller):
    try:
        log_message("INFO", "="*40)
        log_message("INFO", "SYSTEM STATUS")
        log_component_status("Uptime", f"{get_uptime_ms()} ms")
        log_component_status("System ready", system_ready)
        log_component_status("IR movement detected", sensor.is_detected() if sensor else False)
        log_component_status("Servo angle", servo_controller.get_status()['current_angle'])
        log_message("INFO", "="*40)
    except Exception as e:
        log_message("ERROR", f"Status print failed: {e}")

def display_status_if_needed(last_display_time, sensor, system_ready, servo_controller):
    from utime import ticks_ms, ticks_diff
    current_time = ticks_ms()
    if ticks_diff(current_time, last_display_time) > STATUS_UPDATE_INTERVAL_MS:
        print_system_status(sensor, system_ready, servo_controller)
        return current_time
    return last_display_time