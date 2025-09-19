import time
from config import (
    NO_TYPE_SELECTED,
    NEUTRAL_POSITION,
    MSG_SYSTEM_STARTED,
    SYSTEM_READY,
    MOVEMENT_TIMEOUT_MS,
    MSG_TIMEOUT,
    MSG_MOVEMENT_DETECTED,
)
from hardware_utils import log_message
from io_utils import blink_led
from time_utils import get_uptime_ms

# Importação direta dos módulos (SEM WiFi inicialmente)
from serial_comm import serial_comm
from message_processor import message_processor
from disposal_control import initialize_disposal_control
from disposal_process import initialize_disposal_process
from disposal_status import initialize_disposal_status
from sensor import pir_sensor
from servo_control import servo_controller

# Variáveis globais para comunicação (serão inicializadas depois)
wifi_manager = None
udp_comm = None
components_initialized = False

# Inicializa comunicação
def initialize_communication():
    """Initialize communication modules safely with delayed WiFi"""
    global wifi_manager, udp_comm
    log_message("INFO", "Initializing communication systems...")

    # Serial já inicializada
    if serial_comm.initialized:
        log_message("INFO", "Serial communication ready")
    else:
        log_message("WARNING", "Serial communication not initialized")

    # Aguarda estabilização
    import time
    time.sleep_ms(2000)

    # Inicializa WiFi apenas se configurado
    from config import WIFI_SSID, WIFI_PASSWORD
    if WIFI_SSID and WIFI_PASSWORD and WIFI_SSID != "YOUR_NETWORK_NAME":
        from wifi_manager import wifi_manager as wm
        from udp_comm import udp_comm as uc
        wifi_manager = wm
        udp_comm = uc
        log_message("INFO", "Attempting WiFi initialization...")
        try:
            if wifi_manager.initialize():
                log_message("INFO", "WiFi connected")
                udp_comm.start_discovery_service()
            else:
                log_message("WARNING", "WiFi failed - continuing without network")
        except Exception as e:
            log_message("ERROR", f"WiFi initialization failed: {e}")
    else:
        log_message("WARNING", "WiFi not configured - skipping")

    return True

# ⭐⭐ FUNÇÃO SEGURA DE ENVIO DE MENSAGENS
def send_message(message: str):
    """Send message through available channels"""
    try:
        # ⭐⭐ Tenta Serial primeiro (sempre disponível)
        if serial_comm and hasattr(serial_comm, 'send_message'):
            if serial_comm.send_message(message):
                return True
        
        # ⭐⭐ Tenta UDP apenas se WiFi estiver disponível
        if (wifi_manager and udp_comm and 
            hasattr(wifi_manager, 'is_connected') and 
            wifi_manager.is_connected() and
            hasattr(udp_comm, 'send_message')):
            
            return udp_comm.send_message(message)
            
        return False
        
    except Exception as e:
        log_message("ERROR", f"Send message failed: {e}")
        return False

# ⭐⭐ FUNÇÃO SEGURA DE LEITURA DE MENSAGENS
def read_messages():
    """Read messages from all channels"""
    try:
        message_received = False
        
        # ⭐⭐ Lê do Serial
        if serial_comm and hasattr(serial_comm, 'read_data'):
            data = serial_comm.read_data()
            if data:
                message_processor.process_received_data(data, "SERIAL")
                message_received = True
        
        # ⭐⭐ Lê do UDP apenas se WiFi disponível
        if (wifi_manager and udp_comm and 
            hasattr(wifi_manager, 'is_connected') and 
            wifi_manager.is_connected() and
            hasattr(udp_comm, 'read_data')):
            
            data = udp_comm.read_data()
            if data:
                message_processor.process_received_data(data, "UDP")
                message_received = True
                
        return message_received
        
    except Exception as e:
        log_message("ERROR", f"Read messages failed: {e}")
        return False

# ⭐⭐ INICIALIZAÇÃO DO SISTEMA DE DISPOSAL
try:
    disposal_control = initialize_disposal_control(servo_controller, message_processor)
    disposal_status = initialize_disposal_status(message_processor, disposal_control)
    disposal_process = initialize_disposal_process(servo_controller, message_processor, disposal_control)
    
    disposal_system = {
        'control': disposal_control,
        'status': disposal_status,
        'process': disposal_process
    }
    log_message("INFO", "Disposal system initialized")
except Exception as e:
    log_message("ERROR", f"Disposal system initialization failed: {e}")
    # ⭐⭐ Sistema de fallback
    disposal_system = None

# Adicione variável global para controle de callback
last_movement_callback = 0
MOVEMENT_CALLBACK_DEBOUNCE_MS = 5000  # 5 segundos

# ⭐⭐ CONFIGURAÇÃO DO CALLBACK DO SENSOR
def movement_detected_callback():
    global last_movement_callback
    try:
        current_time = time.ticks_ms()
        
        # Evita disparos múltiplos em sequência
        if time.ticks_diff(current_time, last_movement_callback) > MOVEMENT_CALLBACK_DEBOUNCE_MS:
            send_message(f"{MSG_MOVEMENT_DETECTED}:")
            log_message("INFO", "Movement detected")
            last_movement_callback = current_time
        else:
            log_message("DEBUG", "Movement ignored (debounce active)")
    except Exception as e:
        log_message("ERROR", f"Movement callback failed: {e}")

# ⭐⭐ INICIALIZAÇÃO DE COMPONENTES DE HARDWARE
def initialize_servo() -> bool:
    """Initialize servo controller"""
    try:
        return servo_controller.initialize()
    except Exception as e:
        log_message("ERROR", f"Servo initialization failed: {e}")
        return False

def initialize_sensor() -> bool:
    """Initialize PIR sensor"""
    try:
        return pir_sensor.initialize(movement_detected_callback)
    except Exception as e:
        log_message("ERROR", f"Sensor initialization failed: {e}")
        return False

def initialize_system() -> bool:
    """
    Initialize all system components safely
    """
    global system_ready, components_initialized
    
    # ⭐⭐ Evita inicialização dupla
    if components_initialized:
        log_message("INFO", "System already initialized")
        return True
        
    log_message("INFO", "=== SMART TRASH CAN STARTING ===")
    blink_led(2, 200)
    
    # ⭐⭐ Inicializa hardware crítico primeiro
    servo_initialized = initialize_servo()
    sensor_initialized = initialize_sensor()
    
    # ⭐⭐ Inicializa comunicação (pode falhar sem problemas)
    communication_initialized = initialize_communication()
    
    # ⭐⭐ Sistema está pronto se hardware crítico funcionar
    if servo_initialized and sensor_initialized:
        log_message("INFO", "System initialized successfully!")
        system_ready = True
        components_initialized = True  # ⭐⭐ Marca como inicializado
        blink_led(5, 100)  # Success pattern
        return True
    else:
        log_message("ERROR", "Critical hardware initialization failed!")
        blink_led(10, 50)  # Error pattern
        return False

# ⭐⭐ STATUS DO SISTEMA
def print_system_status() -> None:
    """Display the full system status."""
    try:
        log_message("INFO", "="*50)
        log_message("INFO", "        SYSTEM STATUS")
        log_message("INFO", "="*50)
        
        log_message("INFO", f"Uptime: {get_uptime_ms()} ms")
        log_message("INFO", f"System ready: {system_ready}")
        
        # Status do sensor
        try:
            movement_status = pir_sensor.get_status()
            log_message("INFO", f"Sensor: {'READY' if movement_status else 'ERROR'}")
        except:
            log_message("INFO", "Sensor: ERROR")
        
        # Status do servo
        try:
            servo_status = servo_controller.get_status()
            log_message("INFO", f"Servo: {'READY' if servo_status['initialized'] else 'ERROR'}")
        except:
            log_message("INFO", "Servo: ERROR")
        
        # Status WiFi
        try:
            if wifi_manager and hasattr(wifi_manager, 'is_connected'):
                log_message("INFO", f"WiFi: {'CONNECTED' if wifi_manager.is_connected() else 'DISCONNECTED'}")
            else:
                log_message("INFO", "WiFi: NOT INITIALIZED")
        except:
            log_message("INFO", "WiFi: ERROR")
        
        log_message("INFO", "="*50)
        
    except Exception as e:
        log_message("ERROR", f"Status display failed: {e}")

# ⭐⭐ VARIÁVEIS GLOBAIS DO SISTEMA
system_start_time = time.ticks_ms()
last_status_report = 0
system_ready = False

# ⭐⭐ FUNÇÃO PRINCIPAL
def main() -> None:
    """Main function of the smart trash can."""
    global last_status_report, system_ready
    
    log_message("INFO", "==========================================")
    log_message("INFO", "       ESP32 SMART TRASH CAN SYSTEM")
    log_message("INFO", "==========================================")
    
    # Initialize system
    if not initialize_system():
        log_message("ERROR", "Failed to initialize system. Entering recovery mode.")
        
        # ⭐⭐ Modo de recuperação: apenas mantém servo neutro
        try:
            servo_controller.move_to_angle(NEUTRAL_POSITION)
            log_message("INFO", "Servo set to neutral position")
        except Exception as e:
            log_message("ERROR", f"Recovery mode failed: {e}")
        
        return
    
    # Send startup message
    send_message(f"{MSG_SYSTEM_STARTED}:{SYSTEM_READY}")
    log_message("INFO", "Smart Trash Can ready for operation!")
    print_system_status()

    # ⭐⭐ MAIN LOOP SEGURO
    log_message("INFO", "Entering main loop...")
    blink_led(3, 100)
    
    last_status_display = time.ticks_ms()

    while True:
        try:
            current_time = time.ticks_ms()
            
            # ⭐⭐ Lê mensagens periodicamente
            read_messages()
            
            # ⭐⭐ Mostra status a cada 30 segundos
            if time.ticks_diff(current_time, last_status_display) > 30000:
                print_system_status()
                last_status_display = current_time
            
            # ⭐⭐ Processa disposição se condições forem atendidas
            try:
                movement_status = pir_sensor.get_status()
                disposal_status = disposal_system['status'].get_status() if disposal_system else {'is_processing': False}
                
                if (movement_status['movement_detected'] and 
                    not disposal_status['is_processing'] and 
                    message_processor.selected_waste_type != NO_TYPE_SELECTED):
                    
                    log_message("INFO", "Starting disposal process")
                    disposal_system['process'].process_waste_disposal(
                        message_processor.selected_waste_type
                    )

                    # 🔹 Reseta o PIR após iniciar o processo
                    pir_sensor.reset_detection()
                
                # ⭐⭐ Verifica timeout de movimento
                if (movement_status['movement_detected'] and 
                    time.ticks_diff(current_time, movement_status['last_detection_time']) > MOVEMENT_TIMEOUT_MS and
                    not disposal_status['is_processing']):
                    
                    log_message("WARNING", "Movement timeout - no selection made")
                    servo_controller.move_to_angle(NEUTRAL_POSITION)
                    send_message(f"{MSG_TIMEOUT}:NO_SELECTION")
                    pir_sensor.reset_detection()

                    # 🔹 Reseta o PIR após timeout
                    pir_sensor.reset_detection()
                    
            except Exception as e:
                log_message("ERROR", f"Processing error: {e}")
            
            # ⭐⭐ Pequena pausa para evitar sobrecarga
            time.sleep_ms(100)
            
        except Exception as e:
            log_message("CRITICAL", f"Critical error in main loop: {e}")
            log_message("INFO", "Attempting system recovery...")
            
            # ⭐⭐ Tentativa de recuperação
            try:
                servo_controller.move_to_angle(NEUTRAL_POSITION)
                pir_sensor.reset_detection()
                time.sleep_ms(2000)
            except:
                pass
            
            system_ready = False

# ⭐⭐ EXECUÇÃO PRINCIPAL
main()