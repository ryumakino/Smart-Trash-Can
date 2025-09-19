from math_utils import safe_int
from hardware_utils import log_message
from config import NO_TYPE_SELECTED, MSG_TYPE_SELECTED, WASTE_TYPES

class MessageProcessor:
    def __init__(self):
        self.selected_waste_type = NO_TYPE_SELECTED
        self.serial_comm = None
        self.udp_comm = None
        self.wifi_manager = None

    def initialize(self):
        """Initialize with communication instances"""
        # Importação direta
        from serial_comm import serial_comm
        from udp_comm import udp_comm
        from wifi_manager import wifi_manager
        
        self.serial_comm = serial_comm
        self.udp_comm = udp_comm
        self.wifi_manager = wifi_manager

    def process_type_selection(self, type_num: int) -> bool:
        if 0 <= type_num <= 5:
            self.selected_waste_type = type_num
            self.send_message(f"{MSG_TYPE_SELECTED}:{type_num}:{WASTE_TYPES[type_num]}")
            return True
        return False

    def process_received_data(self, data: str, source_channel: str) -> bool:
        clean_data = data.strip().upper()
        
        # Comando para atualizar IP do PC
        if clean_data.startswith("PC_IP:"):
            parts = clean_data.split(":")
            if len(parts) >= 2 and self.udp_comm.update_pc_ip(parts[1]):
                log_message("INFO", f"PC IP updated via command: {parts[1]}")
                self.send_message(f"PC_IP_ACK:{parts[1]}")
                return True
        
        # Processamento normal de comandos
        if clean_data in ['0','1','2','3','4','5']:
            return self.process_type_selection(safe_int(clean_data))
        
        log_message("WARNING", f"Unrecognized command from {source_channel}: {data}")
        return False

    def send_message(self, message: str) -> bool:
        """Send message through available channels"""
        # Tenta primeiro pelo Serial
        if self.serial_comm and self.serial_comm.send_message(message):
            return True
        
        # Se não deu, tenta pelo UDP
        if self.udp_comm and self.udp_comm.send_message(message):
            return True

        return False

    def read_messages(self) -> bool:
        """Read messages from all channels"""
        # Lê do Serial
        if self.serial_comm:
            data = self.serial_comm.read_data()
            if data:
                self.process_received_data(data, "SERIAL")
                return True
        
        # Lê do UDP
        if self.udp_comm:
            data = self.udp_comm.read_data()
            if data:
                self.process_received_data(data, "UDP")
                return True
                
        return False

# Instância global
message_processor = MessageProcessor()
message_processor.initialize()  # Inicializa automaticamente