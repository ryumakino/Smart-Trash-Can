# database_refactored.py – DRY + SOLID
import sqlite3, os, json
from datetime import datetime
from src.core.base_classes import BaseService, ConfigurableMixin

class ClassificationDB(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('system')
        self._db_path = None
        self.init_db()

    # ---------- lifecycle ---------- #
    def initialize(self) -> bool:
        if self._initialized: return True
        try:
            data_dir = self.get_config_value('DATA_DIR', 'data')
            os.makedirs(data_dir, exist_ok=True)
            self._db_path = os.path.join(data_dir, "classifications.db")
            self._initialized = True
            self.logger.success("✅ ClassificationDB inicializado")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização: {e}")
            return False

    # ---------- public api ---------- #
    def init_db(self):
        if not self.initialize(): return False
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    original_class TEXT NOT NULL,
                    system_class TEXT NOT NULL,
                    system_index INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    image_path TEXT,
                    processing_time REAL,
                    model_type TEXT,
                    is_mock BOOLEAN DEFAULT FALSE,
                    device_id TEXT
                )
            """)
            # TABELA DE DISPOSITIVOS EXPANDIDA
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    
                    -- DeviceConfig
                    device_name TEXT,
                    device_type TEXT,
                    device_location TEXT,
                    device_version TEXT,
                    device_manufacturer TEXT,
                    auto_generate_id BOOLEAN DEFAULT FALSE,
                    
                    -- WiFiConfig
                    wifi_ssid TEXT,
                    wifi_max_retries INTEGER,
                    wifi_retry_delay INTEGER,
                    ap_ssid_prefix TEXT,
                    ap_channel INTEGER,
                    
                    -- NetworkConfig
                    ip_address TEXT,
                    network_mode TEXT,
                    udp_port INTEGER,
                    server_port INTEGER,
                    auto_discover_server BOOLEAN,
                    discovery_interval INTEGER,
                    heartbeat_interval INTEGER,
                    enabled_protocols TEXT,
                    
                    -- SystemConfig
                    status_led_pin INTEGER,
                    log_level TEXT,
                    memory_free INTEGER,
                    memory_total INTEGER,
                    
                    -- ServoConfig
                    servo_pin INTEGER,
                    servo_freq INTEGER,
                    servo_min_duty INTEGER,
                    servo_max_duty INTEGER,
                    servo_reset_delay INTEGER,
                    waste_types TEXT,
                    
                    -- IRSensorConfig
                    ir_sensor_pin INTEGER,
                    ir_active_high BOOLEAN,
                    ir_check_interval REAL,
                    ir_detection_threshold INTEGER,
                    
                    -- Status
                    status TEXT DEFAULT 'offline',
                    last_seen TEXT,
                    first_seen TEXT,
                    firmware_version TEXT,
                    model TEXT,
                    classifications_count INTEGER DEFAULT 0,
                    
                    -- Configurações completas (JSON)
                    device_config TEXT,
                    wifi_config TEXT,
                    network_config TEXT,
                    serial_config TEXT,
                    system_config TEXT,
                    servo_config TEXT,
                    ir_config TEXT,
                    error_config TEXT,
                    power_config TEXT,
                    health_config TEXT,
                    
                    -- Timestamps
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Índices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type)")
            
        self.logger.success("✅ Banco de dados inicializado")
        return True

    def save_classification(self, result):
        if not self._initialized: return False
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT INTO classifications 
                (timestamp, original_class, system_class, system_index, confidence,
                 image_path, processing_time, model_type, is_mock, device_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('timestamp', datetime.now().isoformat()),
                result.get('original_class', ''),
                result.get('system_class', ''),
                result.get('system_index', -1),
                result.get('confidence', 0.0),
                result.get('image_path', ''),
                result.get('processing_time', 0.0),
                result.get('model_type', 'unknown'),
                result.get('is_mock', False),
                result.get('device_id', '')
            ))
        return True
    
    # database.py - Método save_device expandido
    def save_device(self, device_data: dict) -> bool:
        """Salva ou atualiza um dispositivo com todas as configurações do ESP32"""
        if not self._initialized: 
            return False
            
        device_id = device_data.get('device_id')
        if not device_id:
            return False
            
        now = datetime.now().isoformat()
        
        # Extrair configurações específicas
        device_config = device_data.get('DeviceConfig', {})
        wifi_config = device_data.get('WiFiConfig', {})
        network_config = device_data.get('NetworkConfig', {})
        serial_config = device_data.get('SerialConfig', {})
        system_config = device_data.get('SystemConfig', {})
        servo_config = device_data.get('ServoConfig', {})
        ir_config = device_data.get('IRSensorConfig', {})
        error_config = device_data.get('ErrorHandlingConfig', {})
        power_config = device_data.get('PowerConfig', {})
        health_config = device_data.get('HealthCheckConfig', {})
        
        with sqlite3.connect(self._db_path) as conn:
            # Verificar se dispositivo já existe
            existing = conn.execute(
                "SELECT device_id FROM devices WHERE device_id = ?", 
                (device_id,)
            ).fetchone()
            
            if existing:
                # Atualizar dispositivo existente
                conn.execute("""
                    UPDATE devices SET 
                    -- DeviceConfig
                    device_name = COALESCE(?, device_name),
                    device_type = COALESCE(?, device_type),
                    device_location = COALESCE(?, device_location),
                    device_version = COALESCE(?, device_version),
                    device_manufacturer = COALESCE(?, device_manufacturer),
                    auto_generate_id = COALESCE(?, auto_generate_id),
                    
                    -- WiFiConfig
                    wifi_ssid = COALESCE(?, wifi_ssid),
                    wifi_max_retries = COALESCE(?, wifi_max_retries),
                    wifi_retry_delay = COALESCE(?, wifi_retry_delay),
                    ap_ssid_prefix = COALESCE(?, ap_ssid_prefix),
                    ap_channel = COALESCE(?, ap_channel),
                    
                    -- NetworkConfig
                    ip_address = ?,
                    network_mode = COALESCE(?, network_mode),
                    udp_port = COALESCE(?, udp_port),
                    server_port = COALESCE(?, server_port),
                    auto_discover_server = COALESCE(?, auto_discover_server),
                    discovery_interval = COALESCE(?, discovery_interval),
                    heartbeat_interval = COALESCE(?, heartbeat_interval),
                    enabled_protocols = COALESCE(?, enabled_protocols),
                    
                    -- SystemConfig
                    status_led_pin = COALESCE(?, status_led_pin),
                    log_level = COALESCE(?, log_level),
                    memory_free = COALESCE(?, memory_free),
                    memory_total = COALESCE(?, memory_total),
                    
                    -- ServoConfig
                    servo_pin = COALESCE(?, servo_pin),
                    servo_freq = COALESCE(?, servo_freq),
                    servo_min_duty = COALESCE(?, servo_min_duty),
                    servo_max_duty = COALESCE(?, servo_max_duty),
                    servo_reset_delay = COALESCE(?, servo_reset_delay),
                    waste_types = COALESCE(?, waste_types),
                    
                    -- IRSensorConfig
                    ir_sensor_pin = COALESCE(?, ir_sensor_pin),
                    ir_active_high = COALESCE(?, ir_active_high),
                    ir_check_interval = COALESCE(?, ir_check_interval),
                    ir_detection_threshold = COALESCE(?, ir_detection_threshold),
                    
                    -- Status
                    status = ?,
                    last_seen = ?,
                    firmware_version = COALESCE(?, firmware_version),
                    model = COALESCE(?, model),
                    
                    -- Configurações completas
                    device_config = COALESCE(?, device_config),
                    wifi_config = COALESCE(?, wifi_config),
                    network_config = COALESCE(?, network_config),
                    serial_config = COALESCE(?, serial_config),
                    system_config = COALESCE(?, system_config),
                    servo_config = COALESCE(?, servo_config),
                    ir_config = COALESCE(?, ir_config),
                    error_config = COALESCE(?, error_config),
                    power_config = COALESCE(?, power_config),
                    health_config = COALESCE(?, health_config),
                    
                    updated_at = ?
                    WHERE device_id = ?
                """, (
                    # DeviceConfig
                    device_config.get('DEVICE_NAME'),
                    device_config.get('DEVICE_TYPE'),
                    device_config.get('DEVICE_LOCATION'),
                    device_config.get('DEVICE_VERSION'),
                    device_config.get('DEVICE_MANUFACTURER'),
                    device_config.get('AUTO_GENERATE_ID', False),
                    
                    # WiFiConfig
                    wifi_config.get('SSID'),
                    wifi_config.get('MAX_RETRIES'),
                    wifi_config.get('RETRY_DELAY'),
                    wifi_config.get('AP_SSID_PREFIX'),
                    wifi_config.get('AP_CHANNEL'),
                    
                    # NetworkConfig
                    device_data.get('ip_address'),
                    network_config.get('NETWORK_MODE'),
                    network_config.get('UDP_PORT'),
                    network_config.get('SERVER_PORT'),
                    network_config.get('AUTO_DISCOVER_SERVER'),
                    network_config.get('DISCOVERY_INTERVAL'),
                    network_config.get('HEARTBEAT_INTERVAL'),
                    json.dumps(network_config.get('ENABLED_PROTOCOLS', [])),
                    
                    # SystemConfig
                    system_config.get('STATUS_LED_PIN'),
                    system_config.get('LOG_LEVEL'),
                    device_data.get('memory_free'),
                    device_data.get('memory_total'),
                    
                    # ServoConfig
                    servo_config.get('SERVO_PIN'),
                    servo_config.get('SERVO_FREQ'),
                    servo_config.get('SERVO_MIN_DUTY'),
                    servo_config.get('SERVO_MAX_DUTY'),
                    servo_config.get('SERVO_RESET_DELAY'),
                    json.dumps(servo_config.get('WASTE_TYPES', [])),
                    
                    # IRSensorConfig
                    ir_config.get('IR_SENSOR_PIN'),
                    ir_config.get('ACTIVE_HIGH'),
                    ir_config.get('CHECK_INTERVAL'),
                    ir_config.get('DETECTION_THRESHOLD'),
                    
                    # Status
                    device_data.get('status', 'online'),
                    device_data.get('last_seen', now),
                    device_config.get('DEVICE_VERSION'),
                    device_config.get('DEVICE_TYPE'),
                    
                    # Configurações completas
                    json.dumps(device_config),
                    json.dumps(wifi_config),
                    json.dumps(network_config),
                    json.dumps(serial_config),
                    json.dumps(system_config),
                    json.dumps(servo_config),
                    json.dumps(ir_config),
                    json.dumps(error_config),
                    json.dumps(power_config),
                    json.dumps(health_config),
                    
                    now,
                    device_id
                ))
            else:
                # Inserir novo dispositivo
                conn.execute("""
                    INSERT INTO devices 
                    (device_id, device_name, device_type, device_location, device_version, 
                    device_manufacturer, auto_generate_id, wifi_ssid, wifi_max_retries,
                    wifi_retry_delay, ap_ssid_prefix, ap_channel, ip_address, network_mode,
                    udp_port, server_port, auto_discover_server, discovery_interval,
                    heartbeat_interval, enabled_protocols, status_led_pin, log_level,
                    memory_free, memory_total, servo_pin, servo_freq, servo_min_duty,
                    servo_max_duty, servo_reset_delay, waste_types, ir_sensor_pin,
                    ir_active_high, ir_check_interval, ir_detection_threshold, status,
                    last_seen, first_seen, firmware_version, model, device_config,
                    wifi_config, network_config, serial_config, system_config, servo_config,
                    ir_config, error_config, power_config, health_config, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device_id,
                    device_config.get('DEVICE_NAME'),
                    device_config.get('DEVICE_TYPE'),
                    device_config.get('DEVICE_LOCATION'),
                    device_config.get('DEVICE_VERSION'),
                    device_config.get('DEVICE_MANUFACTURER'),
                    device_config.get('AUTO_GENERATE_ID', False),
                    wifi_config.get('SSID'),
                    wifi_config.get('MAX_RETRIES'),
                    wifi_config.get('RETRY_DELAY'),
                    wifi_config.get('AP_SSID_PREFIX'),
                    wifi_config.get('AP_CHANNEL'),
                    device_data.get('ip_address'),
                    network_config.get('NETWORK_MODE'),
                    network_config.get('UDP_PORT'),
                    network_config.get('SERVER_PORT'),
                    network_config.get('AUTO_DISCOVER_SERVER'),
                    network_config.get('DISCOVERY_INTERVAL'),
                    network_config.get('HEARTBEAT_INTERVAL'),
                    json.dumps(network_config.get('ENABLED_PROTOCOLS', [])),
                    system_config.get('STATUS_LED_PIN'),
                    system_config.get('LOG_LEVEL'),
                    device_data.get('memory_free'),
                    device_data.get('memory_total'),
                    servo_config.get('SERVO_PIN'),
                    servo_config.get('SERVO_FREQ'),
                    servo_config.get('SERVO_MIN_DUTY'),
                    servo_config.get('SERVO_MAX_DUTY'),
                    servo_config.get('SERVO_RESET_DELAY'),
                    json.dumps(servo_config.get('WASTE_TYPES', [])),
                    ir_config.get('IR_SENSOR_PIN'),
                    ir_config.get('ACTIVE_HIGH'),
                    ir_config.get('CHECK_INTERVAL'),
                    ir_config.get('DETECTION_THRESHOLD'),
                    device_data.get('status', 'online'),
                    device_data.get('last_seen', now),
                    now,  # first_seen
                    device_config.get('DEVICE_VERSION'),
                    device_config.get('DEVICE_TYPE'),
                    json.dumps(device_config),
                    json.dumps(wifi_config),
                    json.dumps(network_config),
                    json.dumps(serial_config),
                    json.dumps(system_config),
                    json.dumps(servo_config),
                    json.dumps(ir_config),
                    json.dumps(error_config),
                    json.dumps(power_config),
                    json.dumps(health_config),
                    now,
                    now
                ))
                
        return True

    def get_recent_classifications(self, limit=50):
        with sqlite3.connect(self._db_path) as conn:
            return conn.execute("""
                SELECT * FROM classifications ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()

    def get_statistics(self):
        with sqlite3.connect(self._db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]
            by_class = dict(conn.execute("""
                SELECT system_class, COUNT(*) FROM classifications GROUP BY system_class
            """).fetchall())
            avg_conf = conn.execute("SELECT AVG(confidence) FROM classifications").fetchone()[0] or 0
            last = conn.execute("""
                SELECT timestamp, system_class, confidence 
                FROM classifications ORDER BY timestamp DESC LIMIT 1
            """).fetchone()
            return {
                'total_classifications': total,
                'classifications_by_type': by_class,
                'average_confidence': round(avg_conf, 3),
                'last_classification': {
                    'timestamp': last[0] if last else None,
                    'class': last[1] if last else None,
                    'confidence': last[2] if last else None
                }
            }

    def get_status(self):
        base = super().get_status()
        base.update({
            'db_path': self._db_path,
            'db_initialized': self._initialized,
            'total_records': self.get_statistics().get('total_classifications', 0)
        })
        return base
    
    # No seu database service (ex: database.py)
    def get_all_devices(self):
        """Obtém todos os dispositivos do banco"""
        try:
            # Exemplo para SQLite
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT device_id, device_name, device_type, status, ip_address, 
                    device_location, last_seen, first_seen, classifications_count,
                    device_version, firmware_version, network_mode, wifi_ssid
                FROM devices 
                WHERE status != 'removed'
                ORDER BY last_seen DESC
            """)
            
            devices = {}
            for row in cursor.fetchall():
                device_id = row[0]
                devices[device_id] = {
                    "device_id": device_id,
                    "device_name": row[1],
                    "device_type": row[2],
                    "status": row[3],
                    "ip_address": row[4],
                    "device_location": row[5],
                    "last_seen": row[6],
                    "first_seen": row[7],
                    "classifications_count": row[8] or 0,
                    "device_version": row[9],
                    "firmware_version": row[10],
                    "network_mode": row[11],
                    "wifi_ssid": row[12]
                }
            
            return devices
        except Exception as e:
            self.logger.error(f"Erro ao buscar dispositivos: {e}")
            return {}

    def get_online_devices(self):
        """Obtém apenas dispositivos online"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT device_id, device_name, status, ip_address, last_seen
                FROM devices 
                WHERE status = 'online'
                ORDER BY last_seen DESC
            """)
            
            devices = {}
            for row in cursor.fetchall():
                device_id = row[0]
                devices[device_id] = {
                    "device_id": device_id,
                    "device_name": row[1],
                    "status": row[2],
                    "ip_address": row[3],
                    "last_seen": row[4]
                }
            
            return devices
        except Exception as e:
            self.logger.error(f"Erro ao buscar dispositivos online: {e}")
            return {}