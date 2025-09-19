import socket, subprocess, os
from config import (
    ESP_HOSTNAME, DISCOVERY_PORT, BROADCAST_IP, DISCOVERY_TIMEOUT,
    DISCOVERY_ATTEMPTS, IS_WINDOWS, PING_COUNT, PING_TIMEOUT
)
from utils import log_info, log_error, log_warning

class Discovery:
    """Responsible for discovering ESP32 IP address."""

    def __init__(self) -> None:
        self.pc_ip = None

    def discover_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            if not local_ip or local_ip.startswith("127."):
                local_ip = socket.gethostbyname(socket.gethostname())
            self.pc_ip = local_ip
            log_info(f"PC Local IP discovered: {local_ip}")
            return local_ip
        except Exception as e:
            log_error(f"Failed to discover local IP: {e}")
            return None

    def discover_esp32_ip(self):
        if not self.pc_ip:
            self.discover_local_ip()

        ip = self._discover_by_broadcast()
        if ip: return ip

        ip = self._discover_by_hostname()
        if ip: return ip

        ip = self._discover_by_arp()
        if ip: return ip

        ip = self._discover_by_network_scan()
        if ip: return ip

        log_error("ESP32 IP not found using any method")
        return None

    def _discover_by_hostname(self):
        try:
            ip = socket.gethostbyname(ESP_HOSTNAME)
            log_info(f"ESP32 found by hostname: {ip}")
            return ip
        except socket.gaierror:
            log_warning(f"Hostname {ESP_HOSTNAME} not resolvable")
            return None

    def _discover_by_arp(self):
        try:
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            lines = result.stdout.split("\n")
            for line in lines:
                if ESP_HOSTNAME.lower() in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[0] if IS_WINDOWS else parts[1].strip("()")
        except Exception as e:
            log_error(f"Error checking ARP: {e}")
        return None

    def _discover_by_broadcast(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(DISCOVERY_TIMEOUT)
            msg = f"DISCOVER_ESP32:PC_IP:{self.pc_ip}"
            for _ in range(DISCOVERY_ATTEMPTS):
                sock.sendto(msg.encode(), (BROADCAST_IP, DISCOVERY_PORT))
                try:
                    data, addr = sock.recvfrom(1024)
                    if data.decode().startswith("ESP32_RESPONSE"):
                        log_info(f"ESP32 responded from {addr[0]}")
                        sock.close()
                        return addr[0]
                except socket.timeout:
                    continue
            sock.close()
        except Exception as e:
            log_error(f"Broadcast error: {e}")
        return None

    def _discover_by_network_scan(self):
        try:
            prefix = ".".join(self.pc_ip.split(".")[:3])
            log_info(f"Scanning network {prefix}.0/24...")
            for i in range(1, 255):
                ip = f"{prefix}.{i}"
                if self._ping(ip):
                    return ip
        except Exception as e:
            log_error(f"Scan error: {e}")
        return None

    def _ping(self, ip):
        cmd = f"ping -n {PING_COUNT} -w {PING_TIMEOUT} {ip}" if IS_WINDOWS else f"ping -c {PING_COUNT} -W {PING_TIMEOUT//1000} {ip}"
        return os.system(cmd) == 0
