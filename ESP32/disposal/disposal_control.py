from utils import log_message, get_uptime_ms
from config import MSG_ERROR, MSG_DISPOSAL_CANCELLED, NO_TYPE_SELECTED

class DisposalControl:
    def __init__(self, servo_controller, message_processor):
        self.servo_controller = servo_controller
        self.message_processor = message_processor
        self.is_processing = False
        self.disposal_start_time = 0
        
    def cancel_disposal(self) -> bool:
        if self.is_processing:
            processing_time = get_uptime_ms() - self.disposal_start_time
            log_message("INFO", f"Disposal cancelled after {processing_time}ms")
            self.servo_controller.move_to_angle(self.servo_controller.NEUTRAL_POSITION)
            self.is_processing = False
            return True
        return False

    def emergency_stop(self) -> bool:
        log_message("WARNING", "EMERGENCY STOP ACTIVATED")
        
        if self.is_processing:
            processing_time = get_uptime_ms() - self.disposal_start_time
            log_message("WARNING", f"Emergency stop during disposal ({processing_time}ms)")
            self.servo_controller.move_to_angle(self.servo_controller.NEUTRAL_POSITION)
            self.is_processing = False
        
        if hasattr(self.message_processor, 'selected_waste_type'):
            self.message_processor.selected_waste_type = NO_TYPE_SELECTED
        return True

    def set_processing(self, processing: bool, start_time: int = 0):
        """Set processing state."""
        self.is_processing = processing
        self.disposal_start_time = start_time

    def get_processing_status(self) -> dict:
        """Get current processing status."""
        return {
            'is_processing': self.is_processing,
            'processing_time': get_uptime_ms() - self.disposal_start_time if self.is_processing else 0,
            'start_time': self.disposal_start_time
        }

# Instância global (será inicializada no main)
disposal_control = None

def initialize_disposal_control(servo_controller, message_processor):
    """Initialize the disposal control system."""
    global disposal_control
    disposal_control = DisposalControl(servo_controller, message_processor)
    return disposal_control