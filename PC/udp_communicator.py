import socket
import threading
import queue
from utils import get_logger
from security import SecurityManager
from config import UDPConfig

logger = get_logger("UDP")

class UDPCommunicator:
    def __init__(self):
        self.port = UDPConfig.UDP_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.settimeout(1.0)

        self.running = True
        self.msg_queue = queue.Queue()

        # Segurança
        self.security = SecurityManager(UDPConfig.AUTH_KEY, UDPConfig.TOKEN_TIMEOUT)

        # Descobre IPs locais
        self.local_ips = self._get_all_local_ips()

        # Thread listener
        self.listener_thread = threading.Thread(target=self._listener, daemon=True)

    def start(self):
        self.listener_thread.start()
        logger.info(f"UDP Communicator iniciado na porta {self.port}")

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        logger.info("UDPCommunicator parado")

    # ----------------- Listener -----------------
    def _listener(self):
        logger.info(f"UDP Listener ativo na porta {self.port}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                ip = addr[0]
                raw_msg = data.decode().strip()

                # Ignora mensagens do próprio PC
                if ip in self.local_ips:
                    continue

                # Decodifica e valida
                msg = self.security.decrypt_message(raw_msg)
                if not msg:
                    logger.warning(f"Mensagem inválida ou não autenticada de {ip}")
                    continue

                self.msg_queue.put((msg, addr))

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Erro no listener: {e}")

    # ----------------- Envio -----------------
    def send_message(self, message, ip="255.255.255.255"):
        try:
            encrypted_msg = self.security.encrypt_message(message)
            self.sock.sendto(encrypted_msg.encode(), (ip, self.port))
            logger.debug(f"[UDP] Enviado para {ip}:{self.port} -> {message}")
        except Exception as e:
            logger.error(f"Erro ao enviar UDP para {ip}: {e}")

    # ----------------- Utilitários -----------------
    def _get_all_local_ips(self):
        ips = ["127.0.0.1"]
        try:
            hostname = socket.gethostname()
            ips.append(socket.gethostbyname(hostname))
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        return ips
