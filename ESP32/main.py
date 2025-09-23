# main.py (ESP32) - Corrigido com Wi-Fi
import time
from config import ESP32Config, SERVO_ANGLES
from utils import get_logger
from sensor import IRSensor
from udp_communicator import UDPCommunicator
from servo_control import ServoController
from network_manager import WiFiManager  # Novo import

logger = get_logger("ESP32_IR_UDP")

class ESP32System:
    def __init__(self):
        self.last_sent = 0
        self.send_cooldown = 2
        self.discovery_attempts = 0
        self.max_discovery_attempts = 5

        # Conecta ao Wi-Fi primeiro
        self.wifi = WiFiManager()
        if not self.wifi.connect():
            logger.error("❌ Não foi possível conectar ao Wi-Fi. Sistema não pode iniciar.")
            return

        self.sensor = IRSensor(callback=self.on_movement, active_high=True)
        self.udp = UDPCommunicator()
        self.servo = ServoController()
        self.pc_ip = None
        self.running = True

    def on_movement(self):
        if not self.wifi.is_connected():
            logger.error("❌ Wi-Fi desconectado. Não é possível enviar mensagem.")
            return
            
        current_time = time.time()
        if current_time - self.last_sent < self.send_cooldown:
            return
            
        self.last_sent = current_time
        
        if self.pc_ip:
            logger.info(f"📡 Movimento detectado! Enviando para {self.pc_ip}")
            self.udp.send("MOVIMENTO_DETECTADO", ip=self.pc_ip)
        else:
            logger.warning("❓ Nenhum PC conhecido. Tentando descobrir...")
            self.discover_pc()

    def discover_pc(self):
        """Tenta descobrir o PC usando diferentes métodos"""
        if self.discovery_attempts >= self.max_discovery_attempts:
            logger.error("🛑 Máximo de tentativas de descoberta atingido")
            return
            
        self.discovery_attempts += 1
        
        # Obtém o IP da rede atual
        my_ip = self.wifi.get_ip()
        if not my_ip:
            logger.error("❌ Não foi possível obter IP local")
            return
            
        logger.info(f"📍 Meu IP: {my_ip}")
        
        # Calcula broadcast baseado no IP atual
        network_prefix = self.get_network_prefix(my_ip)
        if network_prefix:
            broadcast_ip = f"{network_prefix}.255"
            logger.info(f"📡 Tentando broadcast para {broadcast_ip}")
            try:
                self.udp.send("PING", ip=broadcast_ip)
            except Exception as e:
                logger.warning(f"⚠️ Broadcast {broadcast_ip} falhou: {e}")
        
        # Tenta IPs comuns do PC na mesma sub-rede
        if network_prefix:
            common_pc_ips = [
                f"{network_prefix}.100",  # PC comum
                f"{network_prefix}.1",    # Roteador/gateway
                f"{network_prefix}.2",    # Outro dispositivo
                f"{network_prefix}.50",   # Possível PC
            ]
            
            for pc_suffix in common_pc_ips:
                try:
                    logger.info(f"🔍 Tentando IP específico: {pc_suffix}")
                    self.udp.send("PING", ip=pc_suffix)
                except Exception as e:
                    logger.debug(f"🔍 IP {pc_suffix} não alcançável: {e}")

    def get_network_prefix(self, ip):
        """Extrai o prefixo da rede do IP (ex: 192.168.1)"""
        try:
            parts = ip.split('.')
            if len(parts) == 4:
                return '.'.join(parts[:3])
        except:
            pass
        return None

    def handle_message(self, msg, addr):
        """Processa mensagens recebidas via UDP"""
        if not self.wifi.is_connected():
            logger.error("❌ Wi-Fi desconectado. Ignorando mensagem.")
            return
            
        if isinstance(addr, tuple):
            ip_addr = addr[0]
        else:
            ip_addr = addr
            
        self.pc_ip = ip_addr
        self.discovery_attempts = 0  # Reset attempts on successful communication
        
        logger.info(f"📨 Mensagem recebida de {self.pc_ip}: {msg}")

        if msg == "PC_ONLINE":
            logger.success(f"✅ PC {self.pc_ip} conectado.")
        elif msg.startswith("WASTE_TYPE:"):
            try:
                parts = msg.split(":")
                waste_index = int(parts[1])
                waste_name = parts[2] if len(parts) > 2 else f"Tipo {waste_index}"
                logger.info(f"⚙️ Movendo servo para: {waste_name} (ângulo: {SERVO_ANGLES[waste_index]})")
                
                angle = SERVO_ANGLES[waste_index]
                self.servo.move(angle)
                time.sleep(ESP32Config.SERVO_RESET_DELAY)
                self.servo.reset()
                
                self.udp.send(f"RESP:Comando executado - {waste_name}", ip=self.pc_ip)
                logger.success("✅ Servo movido e resetado com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao processar WASTE_TYPE: {e}")
                self.udp.send("RESP:Erro no comando", ip=self.pc_ip)
        else:
            logger.info(f"📨 Mensagem não reconhecida: {msg}")
            self.udp.send("RESP:Mensagem recebida", ip=self.pc_ip)

    def run(self):
        if not self.wifi.is_connected():
            logger.error("❌ Sistema não pode iniciar - Wi-Fi desconectado")
            return
            
        logger.info("🚀 ESP32 rodando. Aguardando movimento e comandos UDP...")
        
        # Tentativa inicial de descoberta
        self.discover_pc()
        
        while self.running:
            try:
                # Verifica conexão Wi-Fi
                if not self.wifi.is_connected():
                    logger.error("❌ Wi-Fi desconectado. Tentando reconectar...")
                    if self.wifi.connect():
                        logger.success("✅ Wi-Fi reconectado!")
                    else:
                        time.sleep(5)
                        continue
                
                msg, addr = self.udp.receive()
                if msg and addr:
                    self.handle_message(msg, addr)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"❌ Erro no loop principal: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
        self.sensor.stop()
        self.servo.reset()
        logger.info("🛑 Sistema parado")


# --- Execução ---
if __name__ == "__main__":
    system = ESP32System()
    try:
        system.run()
    except KeyboardInterrupt:
        system.stop()