import time
import threading
import queue
from config import MLConfig
from utils import get_logger
from ml_model import classify_waste
from udp_communicator import UDPCommunicator

logger = get_logger("PCMessenger")

class PCMessenger:
    def __init__(self):
        self.udp = UDPCommunicator()
        self.running = True
        self.esp_ip = None

        # Thread processador
        self.processor_thread = threading.Thread(target=self._processor, daemon=True)

    def start(self):
        self.udp.start()
        self.processor_thread.start()
        logger.info("PCMessenger iniciado!")

    def stop(self):
        # Envia aviso de desligamento se ESP32 estiver conectado
        if self.esp_ip:
            try:
                self.udp.send_message("PC_OFFLINE", self.esp_ip)
                logger.info(f"Aviso de desligamento enviado ao ESP32 ({self.esp_ip})")
            except Exception as e:
                logger.error(f"Erro ao enviar PC_OFFLINE: {e}")

        self.running = False
        self.udp.stop()
        logger.info("PCMessenger parado")

    # ----------------- Processor -----------------
    def _processor(self):
        while self.running:
            try:
                msg, addr = self.udp.msg_queue.get(timeout=0.5)
                self._process_message(msg, addr)
            except queue.Empty:
                continue

    def _process_message(self, msg, addr):
        ip = addr[0]

        if self.esp_ip != ip:
            self.esp_ip = ip
            logger.success(f"ESP32 conectado: {self.esp_ip}")

        if msg == "PING":
            self.udp.send_message("PC_ONLINE", ip)

        elif msg == "MOVIMENTO_DETECTADO":
            logger.info("Movimento detectado pelo ESP32")

            # Executa classificação do resíduo
            result = classify_waste()
            if result:
                command = f"WASTE_TYPE:{result['index']}:{result['name']}"
                self.udp.send_message(command, ip)
                logger.info("Enviado tipo do lixo!")

        elif msg.startswith("RESP:"):
            logger.info(f"ESP32 respondeu: {msg[5:]}")

        else:
            logger.warning(f"Mensagem não reconhecida: {msg}")

    # ----------------- Descoberta ESP32 -----------------
    def discover_esp32(self, attempts=5, wait=2.0):
        logger.info("Tentando descobrir ESP32...")
        for _ in range(attempts):
            self.udp.send_message("PING")
            start = time.time()
            while time.time() - start < wait:
                if self.esp_ip:
                    logger.success(f"ESP32 encontrado em {self.esp_ip}")
                    return self.esp_ip
                time.sleep(0.1)
        logger.warning("ESP32 não encontrado")
        return None

# ----------------- Execução -----------------
if __name__ == "__main__":
    pc = PCMessenger()
    pc.start()

    try:
        pc.discover_esp32()
        logger.info("Sistema PC pronto. Aguardando comunicação segura...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pc.stop()
