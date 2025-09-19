# main.py
import utime as time
import _thread

from config import (
    NO_TYPE_SELECTED, NEUTRAL_POSITION, MSG_SYSTEM_STARTED, SYSTEM_READY,
    MOVEMENT_TIMEOUT_MS, MSG_TIMEOUT, MSG_MOVEMENT_DETECTED,
    STATUS_UPDATE_INTERVAL_MS, PIR_SENSOR_PIN
)
from hardware_utils import log_message
from io_utils import blink_led
from time_utils import get_uptime_ms
from serial_comm import serial_comm
from message_processor import message_processor
from servo_control import servo_controller
from sensor import sensor_controller  # sensor IR completo com Serial + UDP
from udp_comm import udp_comm
from disposal_control import initialize_disposal_control
from disposal_process import initialize_disposal_process
from disposal_status import initialize_disposal_status
from comm_manager import CommManager

# Sistema
components_initialized = False
system_ready = False
disposal_system = None

# Timer de software para timeout do movimento
movement_timeout_thread = None
MOVEMENT_CALLBACK_DEBOUNCE_MS = 500

def print_system_status():
    """Exibe status completo do sistema."""
    try:
        log_message("INFO", "="*40)
        log_message("INFO", "SYSTEM STATUS")
        log_message("INFO", f"Uptime: {get_uptime_ms()} ms")
        log_message("INFO", f"System ready: {system_ready}")
        status = sensor_controller.is_detected()
        log_message("INFO", f"IR movement detected: {status}")
        status = servo_controller.get_status()
        log_message("INFO", f"Servo angle: {status['current_angle']}")
        log_message("INFO", "="*40)
    except Exception as e:
        log_message("ERROR", f"Status print failed: {e}")

def main():
    # --- Inicialização do sistema ---
    log_message("INFO", "=== SMART TRASH CAN STARTING ===")
    blink_led(2, 200)

    comm = CommManager()
    if comm.detect_channel():
        log_message("INFO", f"Active channel: {comm.get_channel()}")
    else:
        log_message("INFO", "No channel detected!")
        raise SystemExit

    if sensor_controller and servo_controller:
        blink_led(5, 100)
        log_message("INFO", "System initialized successfully!")
        comm.send_message(f"{MSG_SYSTEM_STARTED}:{SYSTEM_READY}")
    else:
        blink_led(10, 50)
        log_message("ERROR", "System failed to initialize")
        return
    
    def movement_callback(detected: bool):
        if detected:
            log_message("INFO", "Movement detected by callback!")
            comm.send_message("IR:DETECTED")
        else:
            log_message("INFO", "Area is free")
            comm.send_message("IR:CLEARED")
        
    # --- Inicia monitoramento do sensor em thread separada ---
    def sensor_task():
        sensor_controller.set_callback(lambda detected: movement_callback(detected))
        sensor_controller.monitor()

    _thread.start_new_thread(sensor_task, ())

    while True:
        try:
            # Leitura de mensagens
            msgs = comm.read_messages()
            for ch, msg in msgs:
                print(f"[{ch}] {msg}")
                
                # Responde a descoberta UDP
                if "DISCOVER" in msg:
                    comm.send_message("HERE")
                
                # Responde a PING
                elif msg == "PING":
                    comm.send_message("PONG")
                
                # Handshake
                elif msg == "ESP32_READY":
                    comm.send_message("PC_ACK")
                
                # Comandos de tipo de lixo
                elif "SET_TYPE:" in msg:
                    try:
                        waste_type = int(msg.split(":")[1])
                        # Processar tipo de lixo
                        log_message("INFO", f"Waste type received: {waste_type}")
                    except:
                        pass

            # Envio periódico de status
            comm.send_message("STATUS:OK")
            time.sleep_ms(500)

        except Exception as e:
            log_message("CRITICAL", f"Critical error: {e}")
            time.sleep_ms(2000)

# Executa main
if __name__ == "__main__":
    main()
