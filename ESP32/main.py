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
from utils import log_message, blink_led, get_uptime_ms
from communication import (
    initialize_communication, 
    read_messages, 
    send_message,
    start_discovery_service,
    message_processor
)
from sensor import pir_sensor
from servo_control import servo_controller
from disposal import initialize_disposal_system

# Global system variables
system_start_time = time.ticks_ms()
last_status_report = 0
system_ready = False

# Inicialize o sistema de disposal
disposal_system = initialize_disposal_system(servo_controller, message_processor)

# Configure o callback do sensor PIR
def movement_detected_callback():
    send_message(f"{MSG_MOVEMENT_DETECTED}:")
    log_message("INFO", "Movement detected")

def initialize_servo() -> bool:
    """Initialize servo controller"""
    return servo_controller.initialize()

def initialize_system() -> bool:
    """
    Initialize all system components.
    
    Returns:
        bool: True if successful, False otherwise
    """
    global system_ready
    
    log_message("INFO", " STARTING SMART TRASH CAN")
    
    # Initialize components
    servo_initialized = initialize_servo()
    communication_initialized = initialize_communication()
    sensor_initialized = pir_sensor.initialize(movement_detected_callback)
    
    # Start discovery service
    discovery_started = start_discovery_service()
    if discovery_started:
        log_message("INFO", "Discovery service started successfully")
    else:
        log_message("WARNING", "Failed to start discovery service")

    if servo_initialized and communication_initialized and sensor_initialized:
        log_message("INFO", "System initialized successfully!")
        system_ready = True
        blink_led(5, 100)  # Success pattern
        return True
    else:
        log_message("ERROR", "System initialization failed!")
        blink_led(10, 50)  # Error pattern (rapid blinking)
        return False

def print_system_status() -> None:
    """Display the full system status."""
    from communication import get_communication_status
    
    comm_status = get_communication_status()
    movement_status = pir_sensor.get_status()
    disposal_status = disposal_system['status'].get_status()
    servo_status = servo_controller.get_status()
    
    log_message("INFO", "="*40)
    log_message("INFO", "      SMART TRASH CAN SYSTEM")
    log_message("INFO", "="*40)
    
    # System info
    log_message("INFO", f"Uptime: {get_uptime_ms()}ms")
    log_message("INFO", f"System ready: {system_ready}")
    
    # Communication status
    log_message("INFO", "COMMUNICATION:")
    log_message("INFO", f"  Active channel: {comm_status['active_channel']}")
    
    # Sensor status
    log_message("INFO", "SENSOR:")
    log_message("INFO", f"  Movement: {'Detected' if movement_status['movement_detected'] else 'None'}")
    if movement_status['movement_detected']:
        log_message("INFO", f"  Time since detection: {movement_status['time_since_detection']}ms")
    
    # Disposal status
    log_message("INFO", "DISPOSAL:")
    log_message("INFO", f"  Processing: {'Yes' if disposal_status['is_processing'] else 'No'}")
    log_message("INFO", f"  Selected type: {disposal_status['selected_waste_type']}")
    log_message("INFO", f"  Name: {disposal_status['selected_waste_name']}")
    if disposal_status['is_processing']:
        log_message("INFO", f"  Processing time: {disposal_status['processing_time_ms']}ms")
    
    # Servo status
    log_message("INFO", "SERVO:")
    log_message("INFO", f"  Initialized: {'Yes' if servo_status['initialized'] else 'No'}")
    log_message("INFO", f"  Current angle: {servo_status['current_angle']}°")

def main() -> None:
    """Main function of the smart trash can."""
    global last_status_report, system_ready
    
    # Initialize system
    if not initialize_system():
        log_message("ERROR", "Failed to initialize system. Entering recovery mode.")
        return
    
    # Send startup message
    send_message(f"{MSG_SYSTEM_STARTED}:{SYSTEM_READY}")
    log_message("INFO", "Smart Trash Can ready for operation!")
    print_system_status()

    # Main loop
    while True:
        try:
            # Read messages from all available channels
            read_messages()

            # Get current status
            movement_status = pir_sensor.get_status()
            disposal_status = disposal_system['status'].get_status()

            # Process disposal when conditions are met
            if (movement_status['movement_detected'] and 
                not disposal_status['is_processing'] and 
                message_processor.selected_waste_type != NO_TYPE_SELECTED):
                
                log_message("INFO", "Starting disposal process")
                disposal_system['process'].process_waste_disposal(
                    message_processor.selected_waste_type
                )

            # Check movement timeout
            if (movement_status['movement_detected'] and 
                time.ticks_diff(time.ticks_ms(), movement_status['last_detection_time']) > MOVEMENT_TIMEOUT_MS and
                not disposal_status['is_processing']):
                
                log_message("ERROR", "Timeout - no selection made.")
                servo_controller.move_to_angle(NEUTRAL_POSITION)
                send_message(f"{MSG_TIMEOUT}:NO_SELECTION")
                pir_sensor.reset_detection()

            # Small pause to avoid overloading system
            time.sleep_ms(50)
            
        except Exception as e:
            log_message("CRITICAL", f"Error in main loop: {e}")
            log_message("INFO", "Attempting system recovery...")
            time.sleep_ms(1000)
            # Attempt to reset system on critical error
            servo_controller.move_to_angle(NEUTRAL_POSITION)
            system_ready = False
            pir_sensor.reset_detection()

if __name__ == "__main__":
    main()