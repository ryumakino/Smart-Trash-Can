from .serial_comm import SerialComm
from .udp_comm import UDPComm
from .wifi_manager import WiFiManager
from .message_processor import MessageProcessor

# Instâncias globais
serial_comm = SerialComm()
udp_comm = UDPComm()
wifi_manager = WiFiManager()
message_processor = MessageProcessor()

# Funções de conveniência
def initialize_communication():
    """Initialize all communication modules"""
    if wifi_manager.initialize():
        udp_comm.start_discovery_service()
    return True

def send_message(message: str):
    """Send message through available channel"""
    return message_processor.send_message(message)

def read_messages():
    """Read messages from all channels"""
    return message_processor.read_messages()

# Expor variáveis importantes
selected_waste_type = message_processor.selected_waste_type