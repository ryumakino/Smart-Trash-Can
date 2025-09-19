import time
from config import NEUTRAL_POSITION, WASTE_PROCESSING_DELAY, WASTE_TYPES
from time_utils import get_uptime_ms
from hardware_utils import log_message

class DisposalProcess:
    def __init__(self, servo_controller, message_processor, disposal_control):
        self.servo_controller = servo_controller
        self.message_processor = message_processor
        self.disposal_control = disposal_control
        
    def _send_disposal_message(self, action: str, waste_type: int = None) -> str:
        """Helper method to send disposal messages."""
        waste_name = WASTE_TYPES[waste_type] if waste_type is not None else "UNKNOWN"
        message = f"{action}:{waste_type}:{waste_name}"
        
        # Envia mensagem através do processador
        if hasattr(self.message_processor, 'send_message'):
            self.message_processor.send_message(message)
            
        return message

    def process_waste_disposal(self, waste_type: int) -> bool:
        """Process waste disposal for the given waste type."""
        if not 0 <= waste_type < len(WASTE_TYPES):
            error_msg = "Invalid waste type, cancelling disposal"
            log_message("ERROR", error_msg)
            return False

        # Configura estado de processamento
        self.disposal_control.set_processing(True, get_uptime_ms())
        
        log_message("INFO", f"Starting disposal for waste type: {waste_type}")
        self._send_disposal_message("DISPOSAL_STARTED", waste_type)

        # Move o servo para a posição do tipo de lixo
        if not self.servo_controller.move_to_waste_type(waste_type):
            self.disposal_control.set_processing(False)
            return False
        
        # Simula o processamento
        time.sleep_ms(WASTE_PROCESSING_DELAY)
        log_message("INFO", "Waiting for disposal...")
        
        time.sleep_ms(3000)

        # Retorna à posição neutra
        log_message("INFO", "Returning to neutral position")
        self.servo_controller.move_to_angle(NEUTRAL_POSITION)
        time.sleep_ms(1500)

        # Finaliza o processamento
        processing_time = get_uptime_ms() - self.disposal_control.disposal_start_time
        log_message("INFO", f"Disposal completed in {processing_time}ms")
        self._send_disposal_message("DISPOSAL_COMPLETED", waste_type)

        self.disposal_control.set_processing(False)
        return True

# Instância global
disposal_process = None

def initialize_disposal_process(servo_controller, message_processor, disposal_control):
    global disposal_process
    disposal_process = DisposalProcess(servo_controller, message_processor, disposal_control)
    return disposal_process