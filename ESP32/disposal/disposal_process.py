import time
from config import PROCESSING_INACTIVE, PROCESSING_ACTIVE, NEUTRAL_POSITION, WASTE_PROCESSING_DELAY, MSG_ERROR, MSG_DISPOSAL_STARTED, MSG_WAITING_DISPOSAL, MSG_DISPOSAL_COMPLETED, PREFIX_TIPO, PREFIX_NOME, PREFIX_CANAL, NO_TYPE_SELECTED
from utils import log_message, is_valid_waste_type, get_waste_name, get_uptime_ms
from servo_control import move_servo, move_servo_angle
from communication import selected_waste_type, send_message, get_active_channel
from .disposal_status import get_disposal_status

is_processing = PROCESSING_INACTIVE
disposal_start_time = 0

def _send_disposal_message(action: str, waste_type: int = None) -> str:
    active_channel = get_active_channel()
    waste_name = get_waste_name(waste_type) if waste_type is not None else "UNKNOWN"
    
    message = f"{action}"
    if waste_type is not None:
        message += f":{PREFIX_TIPO}{waste_type}:{PREFIX_NOME}{waste_name}"
    message += f":{PREFIX_CANAL}{active_channel}"
    
    send_message(message)
    return message

def process_waste_disposal() -> bool:
    global selected_waste_type, is_processing, disposal_start_time

    if not is_valid_waste_type(selected_waste_type):
        error_msg = "Invalid waste type, cancelling disposal"
        log_message("ERROR", error_msg)
        send_message(f"{MSG_ERROR}:{error_msg}")
        move_servo_angle(NEUTRAL_POSITION)
        return False

    is_processing = PROCESSING_ACTIVE
    disposal_start_time = get_uptime_ms()
    _send_disposal_message(MSG_DISPOSAL_STARTED, selected_waste_type)

    if not move_servo(selected_waste_type):
        is_processing = PROCESSING_INACTIVE
        return False
    
    time.sleep_ms(WASTE_PROCESSING_DELAY)
    log_message("INFO", "Waiting for disposal...")
    send_message(MSG_WAITING_DISPOSAL)
    time.sleep_ms(3000)

    log_message("INFO", "Returning to neutral position")
    move_servo_angle(NEUTRAL_POSITION)
    time.sleep_ms(1500)

    processing_time = get_uptime_ms() - disposal_start_time
    log_message("INFO", f"Disposal completed in {processing_time}ms")
    send_message(f"{MSG_DISPOSAL_COMPLETED}:SUCCESS:TIME:{processing_time}")

    selected_waste_type = NO_TYPE_SELECTED
    is_processing = PROCESSING_INACTIVE
    return True
