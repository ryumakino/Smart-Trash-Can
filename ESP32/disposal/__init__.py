from .disposal_process import disposal_process, initialize_disposal_process
from .disposal_status import disposal_status, initialize_disposal_status
from .disposal_control import disposal_control, initialize_disposal_control

# Função para inicializar todo o sistema de disposal
def initialize_disposal_system(servo_controller, message_processor):
    """Initialize the complete disposal system."""
    control = initialize_disposal_control(servo_controller, message_processor)
    status = initialize_disposal_status(message_processor, control)
    process = initialize_disposal_process(servo_controller, message_processor, control)
    
    return {
        'control': control,
        'status': status,
        'process': process
    }