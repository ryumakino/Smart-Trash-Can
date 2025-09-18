import socket
from utils import log_message, blink_led, validate_ip
from config import PC_IP_ADDRESS, UDP_PORT

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.setblocking(False)

def send_udp_message(message: str) -> bool:
    try:
        if not validate_ip(PC_IP_ADDRESS):
            log_message("ERROR", f"Invalid PC IP: {PC_IP_ADDRESS}")
            return False
        addr = (PC_IP_ADDRESS, UDP_PORT)
        udp_socket.sendto(message.encode(), addr)
        blink_led(1, 50)
        log_message("INFO", f"UDP -> {message} to {addr}")
        return True
    except Exception as e:
        log_message("ERROR", f"UDP send failed: {e}")
        return False

def read_udp_data() -> str:
    try:
        data, addr = udp_socket.recvfrom(1024)
        if data:
            message = data.decode().strip()
            blink_led(1, 50)
            log_message("INFO", f"UDP <- {message} from {addr[0]}")
            return message
    except OSError:
        pass
    except Exception as e:
        log_message("ERROR", f"UDP read failed: {e}")
    return ""
