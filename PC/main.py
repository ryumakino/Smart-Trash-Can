import time
from typing import Optional, Any
from camera import capture_image, preprocess_image
from ml_model import load_model, classify_waste, WASTE_TYPES
from utils import log_error, log_success, log_camera, log_info
from pc_messenger import PCMessenger

class PCMessengerHandler(PCMessenger):
    def handle_secure_message(self, msg, addr=None):
        log_info(f"Mensagem segura: {msg}")
        
        if msg == "MOVIMENTO DETECTADO":
            self.on_movement_detected()

    def on_movement_detected(self):
        log_camera("Movimento detectado! Capturando imagem...")
        
        try:
            # Captura e pré-processa imagem
            image = capture_image()
            if image is None:
                log_error("Falha ao capturar imagem")
                return
            
            # Classifica o tipo de resíduo
            waste_type = classify_waste(model, image)
            if waste_type is None:
                log_error("Erro na classificação ML")
                return
            
            if not (0 <= waste_type < len(WASTE_TYPES)):
                log_error(f"Tipo de resíduo inválido: {waste_type}")
                return
            
            # Envia comando para ESP32
            msg = f"WASTE_TYPE:{waste_type}"
            if self.send_command(msg):
                log_success(f"Tipo de resíduo enviado: {waste_type} ({WASTE_TYPES[waste_type]})")
            else:
                log_error("Falha ao enviar comando seguro")
                
        except Exception as e:
            log_error(f"Erro no processamento: {e}")

def discover_loop(pc_handler):
    """Thread para descobrir ESP32 periodicamente"""
    while True:
        if pc_handler.esp_ip is None or not pc_handler.authenticated:
            log_info("Buscando ESP32...")
            pc_handler.discover_esp32(timeout=3)
            
            # Tenta autenticar se encontrou ESP32
            if pc_handler.esp_ip and not pc_handler.authenticated:
                pc_handler._authenticate_udp()
        
        time.sleep(10)

def main():
    # Carrega modelo ML
    global model
    model = load_model()
    
    if model is None:
        log_error("Modelo ML não carregado - usando modo de teste")
    
    # Inicializa comunicação
    pc = PCMessengerHandler()
    pc.start()
    
    # Thread de descoberta
    import threading
    discovery_thread = threading.Thread(target=discover_loop, args=(pc,), daemon=True)
    discovery_thread.start()
    
    log_info("Sistema de classificação de resíduos iniciado!")
    log_info("Aguardando detecção de movimento...")
    
    try:
        while True:
            # Verifica status da conexão
            if not pc.authenticated and pc.esp_ip:
                log_info("Tentando autenticar com ESP32...")
                pc._authenticate_udp()
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        log_info("Encerrando sistema...")
        pc.stop()

if __name__ == "__main__":
    main()