from utils import get_uptime_ms, get_waste_name
from communication import selected_waste_type
from disposal_process import is_processing, disposal_start_time

def get_disposal_status() -> dict:
    processing_time = get_uptime_ms() - disposal_start_time if is_processing else 0
    return {
        'is_processing': is_processing,
        'selected_waste_type': selected_waste_type,
        'selected_waste_name': get_waste_name(selected_waste_type),
        'processing_time_ms': processing_time,
        'start_time': disposal_start_time,
        'timestamp': get_uptime_ms()
    }

def get_disposal_history() -> list:
    # Simples, pode evoluir para persistência
    return [
        {
            'type': selected_waste_type,
            'name': get_waste_name(selected_waste_type),
            'timestamp': get_uptime_ms()
        }
    ]
