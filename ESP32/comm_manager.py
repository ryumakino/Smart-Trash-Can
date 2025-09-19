# comm_manager.py
import utime as time
from hardware_utils import log_message
from serial_comm import SerialComm
from udp_comm import UDPComm

# Configurações
MSG_PING = "PING"
MSG_PONG = "PONG"

class CommManager:
    def __init__(self):
        # --- Serial ---
        self.serial = SerialComm()
        # --- UDP ---
        self.udp = UDPComm()
        # --- Estado ---
        self.active_channel = "NONE"
        self.synchronized = False
        self.last_communication_time = time.ticks_ms()

    # -----------------------------
    # Detecta canal disponível
    # -----------------------------
    def detect_channel(self):
        log_message("INFO", "Detecting communication channel...")

        # --- Testa Serial ---
        if self.serial.initialized:
            try:
                self.serial.send(MSG_PING)
                time.sleep_ms(100)
                msg = self.serial.read()
                if msg and MSG_PONG in msg:
                    self.active_channel = "SERIAL"
                    self.synchronized = True
                    log_message("INFO", "Using SERIAL channel")
                    return True
            except Exception as e:
                log_message("WARNING", f"Serial test failed: {e}")

        # --- Testa UDP ---
        if self.udp.initialize():
            # ESP32 deve aguardar descoberta pelo PC
            log_message("INFO", "UDP initialized, waiting for PC discovery...")
            start_time = time.ticks_ms()
            while time.ticks_diff(time.ticks_ms(), start_time) < 10000:  # 10s timeout
                msg = self.udp.read()
                if msg:
                    text, addr = msg
                    if "DISCOVER" in text:
                        self.udp.send("HERE", addr)
                        self.udp.peer_addr = addr
                        self.active_channel = "UDP"
                        self.synchronized = True
                        log_message("INFO", f"Using UDP channel with {addr}")
                        return True
                time.sleep_ms(100)
            
            log_message("WARNING", "UDP discovery timeout")

        log_message("ERROR", "No communication channel available")
        return False

    # -----------------------------
    # Envia mensagens
    # -----------------------------
    def send_message(self, message: str, addr=None):
        if not self.synchronized:
            log_message("WARNING", "Communication not synchronized")
            return False

        self.last_communication_time = time.ticks_ms()

        if self.active_channel == "SERIAL":
            return self.serial.send(message)

        elif self.active_channel == "UDP":
            return self.udp.send(message, addr)

        else:
            log_message("ERROR", "No active channel")
            return False

    # -----------------------------
    # Lê mensagens
    # -----------------------------
    def read_messages(self):
        msgs = []

        if self.active_channel == "SERIAL":
            msg = self.serial.read()
            if msg:
                msgs.append(("SERIAL", msg))
                self.last_communication_time = time.ticks_ms()

        elif self.active_channel == "UDP":
            msg = self.udp.read()
            if msg:
                text, addr = msg
                msgs.append(("UDP", text))
                self.udp.peer_addr = addr
                self.last_communication_time = time.ticks_ms()

        return msgs

    # -----------------------------
    # Fecha conexões
    # -----------------------------
    def close_connections(self):
        try:
            if self.serial.initialized:
                self.serial.uart.deinit()
        except:
            pass
        try:
            if self.udp.initialized:
                self.udp.sock.close()
        except:
            pass

        self.synchronized = False
        self.active_channel = "NONE"
        log_message("INFO", "All communication connections closed")

    # -----------------------------
    # Status
    # -----------------------------
    def get_channel(self):
        return self.active_channel

    def is_synchronized(self):
        return self.synchronized


# Instância global
comm_manager = CommManager()
