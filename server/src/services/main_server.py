# main_server_refactored.py – DRY + SOLID
import time, threading, queue, json
from src.core.base_classes import BaseService, ConfigurableMixin

class TrashNetServer(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('server')
        self._running = True
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._thread = threading.Thread(target=self._processor_loop, daemon=True)

    # ---------- lifecycle ---------- #
    def initialize(self) -> bool:
        if self._initialized: return True
        self._initialized = True
        self.logger.success("TrashNetServer inicializado")
        return True

    def start(self) -> bool:
        if not self.initialize(): return False
        self.logger.info("Iniciando Servidor TrashNet...")
        self._setup_communicator()
        self._thread.start()
        self._main_loop()
        return True

    def stop(self):
        self._running = False
        from src.core.app_config import get_server_communicator
        comm = get_server_communicator()
        if comm: comm.stop()
        self.logger.info("🛑 Servidor TrashNet parado")

    # ---------- public api ---------- #
    def send_system_command(self, device_id: str, command: str) -> bool:
        try:
            from src.core.app_config import get_server_communicator
            comm = get_server_communicator()
            cmd_map = {"RESTART": "SYSTEM_COMMAND:RESTART", "STATUS": "SYSTEM_COMMAND:STATUS",
                       "DISCOVER": "SYSTEM_COMMAND:DISCOVER", "GET_INFO": "SYSTEM_COMMAND:GET_INFO"}
            if command not in cmd_map:
                self.logger.warning(f"Comando não reconhecido: {command}")
                return False
            return comm.send_to_device(device_id, cmd_map[command])
        except Exception as e:
            self.logger.error(f"Erro ao enviar comando para {device_id}: {e}")
            return False

    def get_system_status(self) -> dict:
        from src.core.app_config import get_server_communicator, get_classification_service, get_database
        comm = get_server_communicator()
        cls = get_classification_service()
        db = get_database()
        return {
            'server': self.get_status(),
            'communication': comm.get_communication_stats() if comm else {},
            'classification_service': cls.get_status() if cls else {},
            'database': db.get_statistics() if db else {}
        }

    # ---------- internal ---------- #
    def _setup_communicator(self):
        from src.core.app_config import get_server_communicator
        comm = get_server_communicator()
        comm.set_movement_callback(self._handle_movement_detected)
        comm.start()

    def _main_loop(self):
        while self._running:
            time.sleep(1)

    def _processor_loop(self):
        while self._running:
            try:
                device_id, device_ip = self._queue.get(timeout=0.1)
                self._process_classification(device_id, device_ip)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Erro no processador: {e}")
                time.sleep(1)

    def _handle_movement_detected(self, device_id: str, device_ip: str):
        self.logger.info(f"🎯 Movimento detectado: {device_id}")
        self._queue.put((device_id, device_ip))

    def _process_classification(self, device_id: str, device_ip: str):
        from src.core.app_config import get_device_registry, get_classification_service, get_server_communicator, get_database
        reg = get_device_registry()
        info = reg.get_device(device_id)
        if not info:
            self.logger.error(f"Dispositivo {device_id} não encontrado")
            return
        cls = get_classification_service()
        result = cls.classify_waste()
        if result:
            self._handle_success(device_id, info.get('device_name', device_id), result)
        else:
            self._handle_failure(device_id)

    def _handle_success(self, device_id: str, name: str, result: dict):
        from src.core.app_config import get_database, get_server_communicator
        db = get_database()
        result['device_id'] = device_id
        db.save_classification(result)
        comm = get_server_communicator()
        idx = result.get('system_index', -1)
        cmd = f"WASTE_TYPE:{idx}:{result['system_class']}"
        if comm.send_to_device(device_id, cmd):
            icon = "🎭" if result.get('is_mock') else "✅"
            self.logger.success(f"{icon} Resíduo classificado para {name}: {result['system_class']} (Confiança: {result['confidence']:.2%})")
            comm.send_to_device(device_id, f"CLASSIFICATION_RESULT:{json.dumps(result)}")

    def _handle_failure(self, device_id: str):
        from src.core.app_config import get_server_communicator
        get_server_communicator().send_to_device(device_id, "WASTE_TYPE:-1:INDETERMINADO")
        self.logger.warning(f"❌ Classificação falhou para {device_id}")