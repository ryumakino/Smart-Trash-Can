import socket
import threading
import time
from config import PCConfig, MLConfig
from utils import get_logger
from ml_model import load_model

logger = get_logger("PC_IR_Receiver")

class PCMessenger:
    def __init__(self, port=PCConfig.UDP_PORT):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('0.0.0.0', self.port))  # Escuta em todas as interfaces
        self.sock.settimeout(1.0)  # Timeout maior para melhor captura
        self.esp_ip = None
        self.running = True

    # Envia mensagem UDP
    def send_message(self, message, ip=None):
        target_ip = ip or '255.255.255.255'
        try:
            self.sock.sendto(message.encode(), (target_ip, self.port))
            logger.info(f"✅ [UDP] Enviado para {target_ip}:{self.port} -> {message}")
        except Exception as e:
            logger.error(f"❌ [UDP] Erro ao enviar para {target_ip}: {e}")

    # Listener UDP em thread separada
    def start_listener(self):
        def listen():
            logger.info(f"👂 Ouvindo na porta {self.port}...")
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    msg = data.decode().strip()

                    # Debug: mostra todas as mensagens recebidas
                    logger.debug(f"📨 Recebido de {addr[0]}:{addr[1]} -> {msg}")

                    # Verifica se é do próprio PC
                    if self.is_local_ip(addr[0]):
                        logger.debug(f"🔄 Ignorando mensagem própria de {addr[0]}")
                        continue

                    # Atualiza IP do ESP32
                    old_ip = self.esp_ip
                    self.esp_ip = addr[0]
                    if old_ip != self.esp_ip:
                        logger.success(f"🔌 ESP32 conectado: {self.esp_ip}")

                    # Processa mensagens
                    self.process_message(msg, addr)

                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"❌ Erro no listener: {e}")

        thread = threading.Thread(target=listen, daemon=True)
        thread.start()
        logger.info("✅ Listener UDP iniciado")

    def is_local_ip(self, ip):
        """Verifica se o IP é local"""
        local_ips = ['127.0.0.1', 'localhost']
        try:
            hostname = socket.gethostname()
            local_ips.append(socket.gethostbyname(hostname))
            
            # Obtém todos os IPs das interfaces de rede
            local_ips.extend(self.get_all_local_ips())
        except:
            pass
        return ip in local_ips

    def get_all_local_ips(self):
        """Obtém todos os IPs locais da máquina"""
        local_ips = []
        try:
            # Conecta a um IP externo para descobrir o IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            local_ips.append(local_ip)
            
            # Adiciona possíveis IPs de rede comum
            if local_ip.startswith('192.168.1.'):
                local_ips.append('192.168.1.255')
            elif local_ip.startswith('192.168.0.'):
                local_ips.append('192.168.0.255')
                
        except Exception as e:
            logger.warning(f"Não foi possível obter IPs locais: {e}")
            
        return local_ips

    def process_message(self, msg, addr):
        """Processa mensagens recebidas"""
        ip = addr[0]
        
        if msg == "PING":
            logger.info(f"📡 PING recebido de {ip}")
            self.send_message("PC_ONLINE", ip)
            logger.info(f"✅ Respondeu PC_ONLINE para {ip}")

        elif msg == "MOVIMENTO_DETECTADO":
            logger.info("🎯 Movimento detectado - processando imagem...")
            waste_index = self.process_image()
            waste_name = MLConfig.WASTE_TYPES[waste_index]
            command = f"WASTE_TYPE:{waste_index}:{waste_name}"
            self.send_message(command, ip)
            logger.info(f"⚙️ Enviado comando: {command}")

        elif msg.startswith("RESP:"):
            logger.info(f"📢 Resposta do ESP32: {msg[5:]}")

        else:
            logger.warning(f"❓ Mensagem não reconhecida: {msg}")

    def process_image(self):
        """Simula o processamento da imagem pelo modelo ML"""
        logger.info("🤖 Processando imagem com modelo ML...")
        load_model()
        time.sleep(2)  # Simula tempo de processamento
        waste_index = 1  # Exemplo: 1 = Plástico
        waste_name = MLConfig.WASTE_TYPES[waste_index]
        logger.info(f"✅ Resíduo detectado: {waste_name}")
        return waste_index

    # Descobre ESP32 via broadcast
    def discover_esp32(self, attempts=5, wait=2.0):
        logger.info("🔍 Procurando ESP32 na rede...")
        
        for i in range(attempts):
            logger.info(f"📡 Tentativa {i+1}/{attempts}...")
            
            # Envia broadcast para sub-rede comum
            network_ips = ["192.168.1.255", "192.168.0.255", "255.255.255.255"]
            for broadcast_ip in network_ips:
                self.send_message("PING", broadcast_ip)
            
            start = time.time()
            while time.time() - start < wait:
                if self.esp_ip:
                    logger.success(f"✅ ESP32 encontrado em {self.esp_ip}")
                    return self.esp_ip
                time.sleep(0.1)
                
        logger.warning("❌ ESP32 não encontrado")
        return None

    def stop(self):
        self.running = False
        self.sock.close()
        logger.info("🛑 Sistema PC parado")


# --- Execução ---
if __name__ == "__main__":
    pc = PCMessenger()
    pc.start_listener()
    
    try:
        # Descobre ESP32 automaticamente
        pc.discover_esp32()
        logger.info("✅ Sistema PC pronto. Aguardando comunicação...")
        
        # Loop principal
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pc.stop()