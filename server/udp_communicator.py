# udp_communicator.py - Comunicação UDP para servidor
import socket
import threading
import queue
import time
from config import UDPConfig
from utils import get_logger
from security import SecurityManager

logger = get_logger("UDPCommunicator")

class UDPCommunicator:
    def __init__(self):
        self.port = UDPConfig.UDP_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.settimeout(UDPConfig.UDP_SOCKET_TIMEOUT)

        self.running = True
        self.msg_queue = queue.Queue()
        self.security = SecurityManager(UDPConfig.AUTH_KEY, UDPConfig.TOKEN_TIMEOUT)
        self.local_ips = self._get_local_ips()

        # Threads
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)

    def _get_local_ips(self):
        """Obter IPs locais para filtrar mensagens próprias"""
        ips = ["127.0.0.1"]
        try:
            hostname = socket.gethostname()
            ips.append(socket.gethostbyname(hostname))
            # Obter IP real
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        return ips

    def start(self):
        """Iniciar comunicador UDP"""
        self.listener_thread.start()
        self.processor_thread.start()
        logger.info(f"UDP Communicator iniciado na porta {self.port}")

    def stop(self):
        """Parar comunicador UDP"""
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        logger.info("UDPCommunicator parado")

    def _listener_loop(self):
        """Loop para receber mensagens UDP"""
        logger.info("UDP Listener iniciado")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(UDPConfig.UDP_BUFFER_SIZE)
                ip = addr[0]
                
                # Ignorar mensagens próprias
                if ip in self.local_ips:
                    continue
                
                raw_msg = data.decode().strip()
                msg = self.security.decrypt_message(raw_msg)
                
                if msg:
                    self.msg_queue.put((msg, addr))
                else:
                    logger.warning(f"Mensagem inválida de {ip}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Erro no listener: {e}")
                time.sleep(1)

    def _processor_loop(self):
        """Processar mensagens recebidas"""
        while self.running:
            try:
                msg, addr = self.msg_queue.get(timeout=1.0)
                self._handle_message(msg, addr)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erro no processador: {e}")

    def _handle_message(self, msg, addr):
        """Manipular mensagem recebida"""
        ip = addr[0]
        
        if msg == "PING":
            self.send_message("PC_ONLINE", ip)
            logger.info(f"Respondendo PING para {ip}")
            
        elif msg == "MOVIMENTO_DETECTADO":
            logger.info(f"Movimento detectado pelo ESP32 ({ip})")
            # A classificação será tratada no main.py
            
        else:
            logger.info(f"Mensagem recebida de {ip}: {msg}")

    def send_message(self, message, ip="255.255.255.255"):
        """Enviar mensagem UDP"""
        try:
            encrypted_msg = self.security.encrypt_message(message)
            self.sock.sendto(encrypted_msg.encode(), (ip, self.port))
            logger.debug(f"UDP → {ip}: {message}")
        except Exception as e:
            logger.error(f"Erro ao enviar para {ip}: {e}")