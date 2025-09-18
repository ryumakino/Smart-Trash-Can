import network
import socket
import time
from machine import UART, Timer
from config import *

# Global variables
selected_waste_type = NO_TYPE_SELECTED
active_communication_channel = CHANNEL_NONE
last_communication_time = 0

serial_uart = UART(0, baudrate=115200)
wlan = network.WLAN(network.STA_IF)
udp_socket = None

# Timer for active channel detection
channel_detection_timer = Timer(0)

def _log_message(direction, message, channel=None, address=None):
    """Centralized logging function for messages"""
    log_msg = f"{direction} {message}"
    if channel:
        log_msg += f" via {channel}"
    if address:
        log_msg += f" from/to {address}"
    print(log_msg)

def _send_serial_message(message):
    """Send message via Serial"""
    global active_communication_channel, last_communication_time
    try:
        serial_uart.write(message + "\n")
        active_communication_channel = CHANNEL_SERIAL
        last_communication_time = time.ticks_ms()
        _log_message("Serial ->", message)
        return True
    except Exception as e:
        print(f"Serial ERROR: {e}")
        return False

def _send_udp_message(message):
    """Send message via UDP"""
    global active_communication_channel, last_communication_time
    try:
        udp_socket.sendto(message.encode(), (PC_IP_ADDRESS, UDP_PORT))
        active_communication_channel = CHANNEL_UDP
        last_communication_time = time.ticks_ms()
        _log_message("UDP ->", message, CHANNEL_UDP, f"{PC_IP_ADDRESS}:{UDP_PORT}")
        return True
    except Exception as e:
        print(f"UDP ERROR: {e}")
        return False

def _read_serial_data():
    """Read data from Serial"""
    global active_communication_channel, last_communication_time
    if serial_uart.any():
        try:
            data = serial_uart.read().decode().strip()
            if data:
                active_communication_channel = CHANNEL_SERIAL
                last_communication_time = time.ticks_ms()
                _log_message("Serial <-", data)
                return data
        except Exception as e:
            print(f"Serial read ERROR: {e}")
    return None

def _read_udp_data():
    """Read data from UDP"""
    global active_communication_channel, last_communication_time
    try:
        data, addr = udp_socket.recvfrom(UDP_BUFFER_SIZE)
        if data:
            message = data.decode().strip()
            active_communication_channel = CHANNEL_UDP
            last_communication_time = time.ticks_ms()
            _log_message("UDP <-", message, CHANNEL_UDP, addr[0])
            return message
    except OSError:
        pass  # No data available
    except Exception as e:
        print(f"UDP read ERROR: {e}")
    return None

# --------------------- Initialization ---------------------

def initialize_wifi():
    """Initialize Wi-Fi with static IP and create UDP socket"""
    global wlan, udp_socket
    print("Setting up Wi-Fi...")
    
    wlan.active(True)
    wlan.ifconfig((ESP_IP, ESP_SUBNET, ESP_GATEWAY, ESP_GATEWAY))
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    start_time = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start_time) < WIFI_CONNECTION_TIMEOUT_MS:
        print("INFO: Connecting to Wi-Fi...")
        time.sleep(1)
    
    if wlan.isconnected():
        print(f"INFO: Wi-Fi connected! IP: {wlan.ifconfig()[0]}")
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setblocking(False)
        print("INFO: UDP socket created")
        return True
    else:
        print("ERROR: Failed to connect Wi-Fi")
        return False

def detect_active_channel(timer=None):
    """Reset active channel if no recent communication"""
    global active_communication_channel, last_communication_time
    if time.ticks_diff(time.ticks_ms(), last_communication_time) > COMMUNICATION_TIMEOUT_MS:
        active_communication_channel = CHANNEL_NONE

def initialize_communication():
    """Initialize Serial and Wi-Fi/UDP communication"""
    global channel_detection_timer
    print("Initializing communication systems...")
 
    try:
        # Test basic write to ensure Serial is functional
        try:
            serial_uart.write("TEST_SERIAL\n")
            print("✅ Serial initialized successfully (115200 baud)")
            return True
        except Exception as e:
            print(f"❌ Serial test failed: {e}")
    except Exception as e:
        print(f"❌ Serial unavailable: {e}")
    
    try:
        wifi_ok = initialize_wifi()
        if wifi_ok:
            print("✅ Wi-Fi/UDP initialized successfully")
            return True
        else:
            print("⚠️ Wi-Fi/UDP not connected")
    except Exception as e:
        print(f"❌ Failed to initialize Wi-Fi/UDP: {e}")
    
    channel_detection_timer.init(period=2000, mode=Timer.PERIODIC, callback=detect_active_channel)
    return False

# --------------------- Sending and Reading ---------------------

def send_message(message):
    """Send message via active or available channel"""
    success = False
    
    # Try Serial first if available
    if USE_SERIAL and serial_uart:
        success = _send_serial_message(message)
    
    # If Serial failed or unavailable, try UDP
    if not success and USE_WIFI and udp_socket and wlan.isconnected():
        success = _send_udp_message(message)
    
    return success

def read_messages():
    """Read messages from all available channels"""
    messages_received = False
    
    # Read from Serial
    if USE_SERIAL:
        data = _read_serial_data()
        if data:
            process_received_data(data, CHANNEL_SERIAL)
            messages_received = True
    
    # Read from UDP
    if USE_WIFI and udp_socket and wlan.isconnected():
        data = _read_udp_data()
        if data:
            process_received_data(data, CHANNEL_UDP)
            messages_received = True
    
    return messages_received

# --------------------- Message Processing ---------------------

def _process_type_selection(type_num):
    """Process waste type selection"""
    global selected_waste_type
    if 0 <= type_num <= 5:
        selected_waste_type = type_num
        send_message(f"{MSG_TYPE_SELECTED}:{type_num}:{WASTE_TYPES[type_num]}")
        return True
    return False

def process_received_data(data, source_channel):
    """Process received data"""
    clean_data = data.strip().upper()
    
    # Direct selection (0-5)
    if clean_data in ['0','1','2','3','4','5']:
        return _process_type_selection(int(clean_data))
    
    # Command SET_TYPE
    if clean_data.startswith(CMD_SET_TYPE) or clean_data.startswith(CMD_TYPE):
        try:
            type_num = int(clean_data.split(":")[1])
            return _process_type_selection(type_num)
        except:
            print("ERROR: Invalid command format")
    
    # Status request
    if clean_data in [CMD_STATUS, CMD_GET_STATUS]:
        send_message(f"{MSG_STATUS}:{PREFIX_CANAL}{active_communication_channel}:{PREFIX_TIPO}{selected_waste_type}")
        return True
    
    print(f"Unrecognized command from {source_channel}: {data}")
    return False

# --------------------- Utilities ---------------------

def get_active_channel():
    return active_communication_channel

def get_communication_status():
    status = {
        'serial_available': USE_SERIAL,
        'wifi_connected': wlan.isconnected() if USE_WIFI else False,
        'active_channel': get_active_channel(),
        'selected_type': selected_waste_type,
        'wifi_ip': wlan.ifconfig()[0] if (USE_WIFI and wlan.isconnected()) else "N/A"
    }
    return status