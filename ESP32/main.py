import uasyncio as asyncio
import time
from typing import Optional
from utils import get_logger
from ir_sensor import IRSensor
from udp_communicator import UDPCommunicator
from servo_control import ServoController
from wlan_manager import WlanManager

logger = get_logger("ESP32_SYSTEM")

class ESP32System:
    def __init__(self):
        self.send_cooldown = 2
        self.last_sent = 0
        self.pc_ip: Optional[str] = None
        self.discovery_success = False
        self.running = False

        # --- Inicializa Wi-Fi ---
        self.wifi = WlanManager()
        if not self.wifi.connect():
            logger.error("Falha ao conectar Wi-Fi")
            return

        # --- Inicializa hardware ---
        self.sensor = IRSensor(callback=self.on_movement_async)
        self.udp = UDPCommunicator()
        self.servo = ServoController()

        self.running = True
        logger.info("ESP32System inicializado")

    async def on_movement_async(self):
        """Callback assíncrono do sensor IR"""
        now = time.time()
        if now - self.last_sent < self.send_cooldown:
            return
        self.last_sent = now

        if self.pc_ip:
            try:
                await self.udp.send_message_async("MOVIMENTO_DETECTADO", ip=self.pc_ip)
            except Exception:
                await self.discover_pc_async()
        else:
            await self.discover_pc_async()

    async def discover_pc_async(self):
        """Descoberta assíncrona de PCs na rede"""
        network_prefix = self.wifi.get_network_prefix()
        if not network_prefix:
            return

        logger.info("Descobrindo PC na rede...")
        for suffix in [255, 100, 1, 2, 50]:
            try:
                await self.udp.send_message_async("PING", ip=f"{network_prefix}.{suffix}")
            except Exception:
                continue
            await asyncio.sleep(0.05)  # pequena pausa entre envios

    async def handle_udp_messages(self):
        """Task principal para processar mensagens recebidas"""
        logger.info("Task UDP iniciada")
        while self.running:
            try:
                msg, addr = await self.udp.msg_queue.get()
                if msg and addr:
                    await self.process_message(msg, addr)
            except Exception as e:
                logger.error(f"Erro no handle_udp_messages: {e}")
                await asyncio.sleep(0.1)

    async def process_message(self, msg, addr):
        """Processa mensagens recebidas do UDP"""
        ip_addr = addr[0] if isinstance(addr, tuple) else addr

        if msg == "PC_ONLINE":
            self.pc_ip = ip_addr
            self.discovery_success = True
            logger.info(f"PC {self.pc_ip} conectado")
        elif msg == "PC_OFFLINE":
            self.pc_ip = None
            self.discovery_success = False
            logger.info("PC desconectado")
        elif msg.startswith("WASTE_TYPE:"):
            try:
                parts = msg.split(":")
                waste_index = int(parts[1])
                waste_name = parts[2] if len(parts) > 2 else f"Tipo {waste_index}"
                self.servo.waste_angles(waste_index, waste_name)
            except Exception as e:
                logger.error(f"Erro processando WASTE_TYPE: {e}")
        else:
            logger.info(f"Mensagem não reconhecida: {msg}")

    async def run_async(self):
        """Loop principal assíncrono"""
        logger.info("ESP32 rodando...")
        self.sensor.start()
        await self.udp.start()
        # Cria task do listener UDP
        udp_task = asyncio.create_task(self.handle_udp_messages())

        while self.running:
            await asyncio.sleep(1)  # loop principal leve, sem bloquear

        udp_task.cancel()

    def stop(self):
        self.running = False
        self.sensor.stop()
        self.servo.reset()
        self.udp.stop()
        logger.info("Sistema parado")


if __name__ == "__main__":
    system = ESP32System()
    if system.running:
        try:
            asyncio.run(system.run_async())
        except KeyboardInterrupt:
            system.stop()
    else:
        logger.error("Sistema não inicializado. Encerrando...")
