import time
from config import *
from servo_control import move_servo, move_servo_angle
from communication import selected_waste_type, send_message, get_active_channel

# Disposal process state
is_processing = PROCESSING_INACTIVE

def _send_disposal_message(action, waste_type=None):
    """Send a standardized disposal message"""
    active_channel = get_active_channel()
    waste_name = WASTE_TYPES[waste_type] if waste_type is not None and 0 <= waste_type < len(WASTE_TYPES) else "UNKNOWN"
    
    message = f"{action}"
    if waste_type is not None:
        message += f":{PREFIX_TIPO}{waste_type}:{PREFIX_NOME}{waste_name}"
    message += f":{PREFIX_CANAL}{active_channel}"
    
    send_message(message)
    return message

def process_waste_disposal():
    """Process the disposal of waste according to the selected type"""
    global selected_waste_type, is_processing

    # Validate selected type
    if selected_waste_type < 0 or selected_waste_type >= len(WASTE_TYPES):
        error_msg = "Invalid waste type, cancelling disposal"
        print(f"ERROR: {error_msg}")
        send_message(f"{MSG_ERROR}:{error_msg}")
        move_servo_angle(NEUTRAL_POSITION)
        return False

    # Mark processing as active
    is_processing = PROCESSING_ACTIVE
    
    _send_disposal_message(MSG_DISPOSAL_STARTED, selected_waste_type)

    # Move servo to the position corresponding to the selected waste type
    if not move_servo(selected_waste_type):
        is_processing = PROCESSING_INACTIVE
        return False
    
    time.sleep(WASTE_PROCESSING_DELAY)

    # Wait for user to dispose the waste
    print("INFO: Waiting for disposal...")
    send_message(MSG_WAITING_DISPOSAL)
    time.sleep(3)  # Time for user to discard the waste

    # Return servo to neutral position
    print("INFO: Returning to neutral position")
    move_servo_angle(NEUTRAL_POSITION)
    time.sleep(1.5)

    # Disposal completed successfully
    print("OK: Disposal completed")
    send_message(f"{MSG_DISPOSAL_COMPLETED}:SUCCESS")

    # Reset states
    selected_waste_type = NO_TYPE_SELECTED
    is_processing = PROCESSING_INACTIVE
    
    return True

def get_disposal_status():
    """Return the current status of the disposal process"""
    return {
        'is_processing': is_processing,
        'selected_waste_type': selected_waste_type,
        'selected_waste_name': WASTE_TYPES[selected_waste_type] if selected_waste_type >= 0 else "None"
    }

def cancel_disposal():
    """Cancel the ongoing disposal process"""
    global is_processing
    
    if is_processing:
        print("INFO: Disposal cancelled")
        send_message(f"{MSG_DISPOSAL_CANCELLED}:MANUAL")
        move_servo_angle(NEUTRAL_POSITION)
        
        is_processing = PROCESSING_INACTIVE
        return True
    
    return False