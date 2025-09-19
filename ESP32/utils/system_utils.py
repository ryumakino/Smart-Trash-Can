import time
from .hardware_utils import log_message

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