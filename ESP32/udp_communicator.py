import usocket as socket
import uasyncio as asyncio
import ujson
from security import SecurityManager
from config import NetworkConfig
class UDPCommunicator:
    def __init__(self):
        self.port = NetworkConfig.UDP_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("0.0.0.0", self.port))

        self.security = SecurityManager(NetworkConfig.AUTH_KEY, NetworkConfig.TOKEN_TIMEOUT)
        self.running = True
        self.msg_queue = asyncio.Queue()

    async def start(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._listener())
        await asyncio.sleep(0)  # Ensures the function uses an async feature

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        print("UDPCommunicatorESP32 parado")

    async def _listener(self):
        print("UDP Listener ativo na porta", self.port)
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
            except OSError:
                await asyncio.sleep(0.05)
                continue

            raw_msg = data.decode().strip()
            msg = self.security.decrypt_message(raw_msg)
            if not msg:
                print("Mensagem inválida de", addr)
                continue

            await self.msg_queue.put((msg, addr))

    def send_message(self, message, ip="255.255.255.255"):
        try:
            encrypted = self.security.encrypt_message(message)
            self.sock.sendto(encrypted.encode(), (ip, self.port))
            print("[UDP] Enviado para", ip, "->", message)
        except Exception as e:
            print("Erro ao enviar:", e)
