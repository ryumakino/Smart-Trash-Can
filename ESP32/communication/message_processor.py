from utils import safe_int, json_encode, log_message
from config import NO_TYPE_SELECTED, MSG_TYPE_SELECTED, WASTE_TYPES, CMD_SET_TYPE, CMD_TYPE, CMD_STATUS, CMD_GET_STATUS, MSG_STATUS, CHANNEL_SERIAL, CHANNEL_UDP
from communication.channel_manager import update_channel, get_active_channel
from communication.serial_comm import send_serial_message, read_serial_data
from communication.udp_comm import send_udp_message, read_udp_data
from utils import create_status_dict

selected_waste_type = NO_TYPE_SELECTED

def process_type_selection(type_num: int) -> bool:
    global selected_waste_type
    if 0 <= type_num <= 5:
        selected_waste_type = type_num
        send_message(f"{MSG_TYPE_SELECTED}:{type_num}:{WASTE_TYPES[type_num]}")
        return True
    return False

def process_received_data(data: str, source_channel: str) -> bool:
    clean_data = data.strip().upper()
    
    if clean_data in ['0','1','2','3','4','5']:
        return process_type_selection(safe_int(clean_data))
    
    if clean_data.startswith(CMD_SET_TYPE) or clean_data.startswith(CMD_TYPE):
        parts = clean_data.split(":")
        if len(parts) >= 2:
            type_num = safe_int(parts[1], NO_TYPE_SELECTED)
            return process_type_selection(type_num)
    
    if clean_data in [CMD_STATUS, CMD_GET_STATUS]:
        status_msg = f"{MSG_STATUS}:{get_active_channel()}:{selected_waste_type}"
        send_message(status_msg)
        return True
    
    log_message("WARNING", f"Unrecognized command from {source_channel}: {data}")
    return False

def send_message(message: str) -> bool:
    active_channel = get_active_channel()
    success = False
    
    if active_channel == CHANNEL_SERIAL:
        success = send_serial_message(message)
    elif active_channel == CHANNEL_UDP:
        success = send_udp_message(message)
    
    if not success:
        success = send_serial_message(message) or send_udp_message(message)
    
    return success

def read_messages() -> bool:
    messages_received = False
    data = read_serial_data()
    if data:
        process_received_data(data, CHANNEL_SERIAL)
        messages_received = True
    data = read_udp_data()
    if data:
        process_received_data(data, CHANNEL_UDP)
        messages_received = True
    return messages_received

def send_system_status() -> bool:
    try:
        status = create_status_dict()
        status['selected_type'] = selected_waste_type
        status['active_channel'] = get_active_channel()
        status_json = json_encode(status)
        return send_message(f"{MSG_STATUS}_FULL:{status_json}")
    except Exception as e:
        log_message("ERROR", f"Failed to send system status: {e}")
        return False
