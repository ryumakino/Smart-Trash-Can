import network
import time
from utils import log_message, validate_ip
from config import ESP_IP, ESP_GATEWAY, ESP_SUBNET, WIFI_SSID, WIFI_PASSWORD, WIFI_CONNECTION_TIMEOUT_MS

wlan = network.WLAN(network.STA_IF)

def initialize_wifi() -> bool:
    log_message("INFO", "Setting up Wi-Fi...")
    try:
        wlan.active(True)
        if validate_ip(ESP_IP) and validate_ip(ESP_GATEWAY):
            wlan.ifconfig((ESP_IP, ESP_SUBNET, ESP_GATEWAY, ESP_GATEWAY))
            log_message("INFO", f"Static IP set: {ESP_IP}")

        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        start_time = time.ticks_ms()
        while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start_time) < WIFI_CONNECTION_TIMEOUT_MS:
            log_message("INFO", "Connecting to Wi-Fi...")
        if wlan.isconnected():
            log_message("INFO", f"Wi-Fi connected! IP: {wlan.ifconfig()[0]}")
            return True
        else:
            log_message("ERROR", "Failed to connect Wi-Fi")
            return False
    except Exception as e:
        log_message("ERROR", f"Wi-Fi setup failed: {e}")
        return False
