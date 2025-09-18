import time
from config import *
from communication import (
    initialize_communication, 
    read_messages, 
    selected_waste_type,
    get_active_channel,
    get_communication_status,
    send_message
)
from servo_control import initialize_servo, move_servo_angle, get_servo_status
from waste_disposal import process_waste_disposal, is_processing, get_disposal_status, cancel_disposal
from sensor import detect_movement, get_movement_status

# Global system variables
system_start_time = time.ticks_ms()
last_status_report = 0

def print_system_status():
    """Displays the full system status"""
    comm_status = get_communication_status()
    movement_status = get_movement_status()
    disposal_status = get_disposal_status()
    servo_status = get_servo_status()
    
    print("\n" + "="*50)
    print("          SMART TRASH CAN SYSTEM")
    print("="*50)
    
    # Communication status
    print("COMMUNICATION:")
    print(f"  Active channel: {comm_status['active_channel']}")
    print(f"  Serial: {'Available' if comm_status['serial_available'] else 'Unavailable'}")
    print(f"  Wi-Fi: {'Connected' if comm_status['wifi_connected'] else 'Disconnected'}")
    if comm_status['wifi_connected']:
        print(f"  IP: {comm_status['wifi_ip']}")
    
    # Sensor status
    print("\nSENSOR:")
    print(f"  Movement: {'Detected' if movement_status['movement_detected'] else 'None'}")
    if movement_status['movement_detected']:
        print(f"  Time since detection: {movement_status['time_since_detection']}ms")
    
    # Disposal status
    print("\nDISPOSAL:")
    print(f"  Processing: {'Yes' if disposal_status['is_processing'] else 'No'}")
    print(f"  Selected type: {disposal_status['selected_waste_type']}")
    print(f"  Name: {disposal_status['selected_waste_name']}")
    
    # Servo status
    print("\nSERVO:")
    print(f"  Initialized: {'Yes' if servo_status['initialized'] else 'No'}")
    print(f"  Neutral position: {servo_status['neutral_position']}°")
    
    print("="*50)
    print("Commands: 0-5, SET_TYPE:X, STATUS, HELP, CANCEL")
    print("="*50 + "\n")

def handle_system_commands(command):
    """Processes special system commands"""
    command = command.upper().strip()
    
    if command in [CMD_SHUTDOWN, CMD_RESTART]:
        print("INFO: Restarting system...")
        send_message(MSG_SYSTEM_RESTARTING)
        time.sleep(2)
        print("INFO: System restarted")
        send_message(f"{MSG_SYSTEM_STARTED}:{SYSTEM_READY}")
        return True
        
    elif command == CMD_RESET:
        print("INFO: Resetting system states...")
        global selected_waste_type
        selected_waste_type = NO_TYPE_SELECTED
        move_servo_angle(NEUTRAL_POSITION)
        send_message(MSG_SYSTEM_RESET)
        return True
        
    elif command == CMD_CANCEL:
        if cancel_disposal():
            send_message(f"{MSG_DISPOSAL_CANCELLED}:MANUAL")
            return True
    
    return False

def main():
    """Main function of the smart trash can"""
    global last_status_report
    
    # Initialize components
    print("="*50)
    print(" STARTING SMART TRASH CAN")
    print("="*50)
    
    initialize_servo()
    communication_initialized = initialize_communication()
    
    if communication_initialized:
        print("INFO: Communication system initialized successfully!")
    else:
        print("WARNING: Communication system with limitations")
    
    print("INFO: Smart Trash Can ready for operation!")
    print_system_status()
    
    # Send startup message
    send_message(f"{MSG_SYSTEM_STARTED}:{SYSTEM_READY}")

    # Main loop
    while True:
        try:
            # Detect movement
            current_movement = detect_movement()

            # Read messages from all available channels
            read_messages()

            # Periodic status report
            current_time = time.ticks_ms()
            if time.ticks_diff(current_time, last_status_report) > STATUS_REPORT_INTERVAL:
                print_system_status()
                last_status_report = current_time
                
                # Send status via communication
                active_channel = get_active_channel()
                send_message(f"{MSG_STATUS}_PERIODIC:{PREFIX_CANAL}{active_channel}")

            # Process disposal when conditions are met
            movement_status = get_movement_status()
            if (movement_status['movement_detected'] and 
                not is_processing and 
                selected_waste_type != NO_TYPE_SELECTED):
                
                active_channel = get_active_channel()
                print(f"INFO: Starting disposal via {active_channel}")
                process_waste_disposal()

            # Check movement timeout
            if (movement_status['movement_detected'] and 
                time.ticks_diff(time.ticks_ms(), movement_status['time_since_detection']) > MOVEMENT_TIMEOUT_MS and
                not is_processing):
                
                print("ERROR: Timeout - no selection made.")
                move_servo_angle(NEUTRAL_POSITION)
                send_message(f"{MSG_TIMEOUT}:NO_SELECTION")

            # Small pause to avoid overloading system
            time.sleep(0.05)
            
        except Exception as e:
            print(f"CRITICAL ERROR in main loop: {e}")
            print("INFO: Attempting system recovery...")
            time.sleep(1)
            # Attempt to reset system on critical error
            move_servo_angle(NEUTRAL_POSITION)

if __name__ == "__main__":
    main()