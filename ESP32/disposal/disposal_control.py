from utils import log_message, get_uptime_ms
from servo_control import move_servo_angle
from communication import selected_waste_type, send_message
from disposal_process import is_processing, PROCESSING_INACTIVE, NEUTRAL_POSITION, PROCESSING_ACTIVE, disposal_start_time
from config import MSG_ERROR, MSG_DISPOSAL_CANCELLED, NO_TYPE_SELECTED
def cancel_disposal() -> bool:
    global is_processing
    if is_processing:
        processing_time = get_uptime_ms() - disposal_start_time
        log_message("INFO", f"Disposal cancelled after {processing_time}ms")
        send_message(f"{MSG_DISPOSAL_CANCELLED}:MANUAL:TIME:{processing_time}")
        move_servo_angle(NEUTRAL_POSITION)
        is_processing = PROCESSING_INACTIVE
        return True
    return False

def emergency_stop() -> bool:
    global is_processing, selected_waste_type
    log_message("WARNING", "EMERGENCY STOP ACTIVATED")
    send_message(f"{MSG_ERROR}:EMERGENCY_STOP")
    
    if is_processing:
        processing_time = get_uptime_ms() - disposal_start_time
        log_message("WARNING", f"Emergency stop during disposal ({processing_time}ms)")
        move_servo_angle(NEUTRAL_POSITION)
        is_processing = PROCESSING_INACTIVE
    
    selected_waste_type = NO_TYPE_SELECTED
    return True
