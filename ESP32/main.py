import time
from config import (
    CMD_SHUTDOWN,
    CMD_RESTART,
    CMD_RESET,
    CMD_CANCEL,
    MSG_SYSTEM_RESTARTING,
    NO_TYPE_SELECTED,
    NEUTRAL_POSITION,
    MSG_SYSTEM_RESET,
    MSG_DISPOSAL_CANCELLED,
    MSG_SYSTEM_STARTED,
    SYSTEM_READY,
    STATUS_REPORT_INTERVAL,
    MOVEMENT_TIMEOUT_MS,
    MSG_TIMEOUT
)
from utils import log_message, get_uptime, blink_led, create_status_dict, soft_reset
from communication import (
    initialize_communication, 
    read_messages, 
    selected_waste_type,
    get_active_channel,
    get_communication_status,
    send_message,
    send_system_status
)
from servo_control import initialize_servo, move_servo_angle, get_servo_status, test_servo_range
from disposal import process_waste_disposal, is_processing, get_disposal_status, cancel_disposal, emergency_stop
from sensor import detect_movement, get_movement_status, reset_movement_detection

# Global system variables
system_start_time = time.ticks_ms()
last_status_report = 0
system_ready = False

def print_system_status() -> None:
    """Display the full system status."""
    comm_status = get_communication_status()
    movement_status = get_movement_status()
    disposal_status = get_disposal_status()
    servo_status = get_servo_status()
    system_status = create_status_dict()
    
    log_message("INFO", "="*40)
    log_message("INFO", "      SMART TRASH CAN SYSTEM")
    log_message("INFO", "="*40)
    
    # System info
    log_message("INFO", f"Uptime: {get_uptime()}")
    log_message("INFO", f"System ready: {system_ready}")
    log_message("INFO", f"Free memory: {system_status['free_memory']}")
    log_message("INFO", f"CPU freq: {system_status['cpu_freq']}MHz")
    log_message("INFO", f"Temperature: {system_status['temperature']:.1f}°C")
    
    # Communication status
    log_message("INFO", "COMMUNICATION:")
    log_message("INFO", f"  Active channel: {comm_status['active_channel']}")
    log_message("INFO", f"  Serial: {'Available' if comm_status['serial_available'] else 'Unavailable'}")
    log_message("INFO", f"  Wi-Fi: {'Connected' if comm_status['wifi_connected'] else 'Disconnected'}")
    if comm_status['wifi_connected']:
        log_message("INFO", f"  IP: {comm_status['wifi_ip']}")
    
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
    log_message("INFO", f"  Neutral position: {servo_status['neutral_position']}°")
    
    log_message("INFO", "="*40)
    log_message("INFO", "Commands: 0-5, SET_TYPE:X, STATUS, HELP, CANCEL, TEST")
    log_message("INFO", "="*40)

def handle_system_commands(command: str) -> bool:
    """
    Process special system commands.
    
    Args:
        command: Command string
        
    Returns:
        bool: True if command was handled, False otherwise
    """
    command = command.upper().strip()
    
    if command in [CMD_SHUTDOWN, CMD_RESTART]:
        log_message("INFO", "Restarting system...")
        send_message(MSG_SYSTEM_RESTARTING)
        time.sleep_ms(2000)
        soft_reset()
        return True
        
    elif command == CMD_RESET:
        log_message("INFO", "Resetting system states...")
        global selected_waste_type
        selected_waste_type = NO_TYPE_SELECTED
        move_servo_angle(NEUTRAL_POSITION)
        reset_movement_detection()
        send_message(MSG_SYSTEM_RESET)
        return True
        
    elif command == CMD_CANCEL:
        if cancel_disposal():
            send_message(f"{MSG_DISPOSAL_CANCELLED}:MANUAL")
            return True
    
    elif command == "TEST":
        log_message("INFO", "Running system tests...")
        test_result = test_servo_range()
        send_message(f"TEST_RESULT:{'PASS' if test_result else 'FAIL'}")
        return True
    
    elif command == "EMERGENCY_STOP" and emergency_stop():
        send_message("EMERGENCY_STOP:ACTIVATED")
        return True
    
    return False

def initialize_system() -> bool:
    """
    Initialize all system components.
    
    Returns:
        bool: True if successful, False otherwise
    """
    global system_ready
    
    log_message("INFO", "="*40)
    log_message("INFO", " STARTING SMART TRASH CAN")
    log_message("INFO", "="*40)
    
    # Initialize components
    servo_initialized = initialize_servo()
    communication_initialized = initialize_communication()
    
    if servo_initialized and communication_initialized:
        log_message("INFO", "System initialized successfully!")
        system_ready = True
        blink_led(5, 100)  # Success pattern
        return True
    else:
        log_message("ERROR", "System initialization failed!")
        blink_led(10, 50)  # Error pattern (rapid blinking)
        return False

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

            # Detect movement (polling fallback)
            detect_movement()

            # Periodic status report
            current_time = time.ticks_ms()
            if time.ticks_diff(current_time, last_status_report) > STATUS_REPORT_INTERVAL:
                print_system_status()
                last_status_report = current_time
                
                # Send comprehensive status
                send_system_status()

            # Process disposal when conditions are met
            movement_status = get_movement_status()
            if (movement_status['movement_detected'] and 
                not is_processing and 
                selected_waste_type != NO_TYPE_SELECTED):
                
                active_channel = get_active_channel()
                log_message("INFO", f"Starting disposal via {active_channel}")
                process_waste_disposal()

            # Check movement timeout
            if (movement_status['movement_detected'] and 
                time.ticks_diff(time.ticks_ms(), movement_status['time_since_detection']) > MOVEMENT_TIMEOUT_MS and
                not is_processing):
                
                log_message("ERROR", "Timeout - no selection made.")
                move_servo_angle(NEUTRAL_POSITION)
                send_message(f"{MSG_TIMEOUT}:NO_SELECTION")

            # Small pause to avoid overloading system
            time.sleep_ms(50)
            
        except Exception as e:
            log_message("CRITICAL", f"Error in main loop: {e}")
            log_message("INFO", "Attempting system recovery...")
            time.sleep_ms(1000)
            # Attempt to reset system on critical error
            move_servo_angle(NEUTRAL_POSITION)
            system_ready = False

if __name__ == "__main__":
    main()