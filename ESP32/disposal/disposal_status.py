from utils import get_uptime_ms
from config import WASTE_TYPES

class DisposalStatus:
    def __init__(self, message_processor, disposal_control):
        self.message_processor = message_processor
        self.disposal_control = disposal_control
        self.history = []
        
    def get_status(self) -> dict:
        """Get current disposal status."""
        processing_time = 0
        if self.disposal_control.is_processing:
            processing_time = get_uptime_ms() - self.disposal_control.disposal_start_time
            
        selected_type = getattr(self.message_processor, 'selected_waste_type', -1)
        
        return {
            'is_processing': self.disposal_control.is_processing,
            'selected_waste_type': selected_type,
            'selected_waste_name': WASTE_TYPES[selected_type],
            'processing_time_ms': processing_time,
            'start_time': self.disposal_control.disposal_start_time,
            'timestamp': get_uptime_ms()
        }

    def add_to_history(self, waste_type: int):
        """Add disposal to history."""
        self.history.append({
            'type': waste_type,
            'name': WASTE_TYPES[waste_type],
            'timestamp': get_uptime_ms()
        })
        
        # Mantém apenas os últimos 10 itens no histórico
        if len(self.history) > 10:
            self.history.pop(0)

    def get_history(self) -> list:
        """Get disposal history."""
        return self.history

# Instância global (será inicializada no main)
disposal_status = None

def initialize_disposal_status(message_processor, disposal_control):
    """Initialize the disposal status system."""
    global disposal_status
    disposal_status = DisposalStatus(message_processor, disposal_control)
    return disposal_status