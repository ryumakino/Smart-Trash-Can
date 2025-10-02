# network_utils.py - Utilitários de rede reutilizáveis
import time
import ubinascii
import network
from utils import get_logger

logger = get_logger("NetworkUtils")

class NetworkInfoBuilder:
    @staticmethod
    def build_connection_info(sta_if, ap_if, wifi_config, success, mode, connected, ap_mode, ip):
        """Construir informações de conexão de forma unificada"""
        connection_info = {
            'success': success,
            'mode': mode,
            'connected': connected,
            'ap_mode': ap_mode,
            'timestamp': time.time()
        }
        
        if mode == 'STA' and success:
            ifconfig = sta_if.ifconfig()
            connection_info.update({
                'ip': ifconfig[0],
                'subnet': ifconfig[1],
                'gateway': ifconfig[2],
                'dns': ifconfig[3],
                'ssid': wifi_config.get('SSID'),
                'rssi': NetworkInfoBuilder._get_rssi(sta_if),
                'mac': NetworkInfoBuilder._get_mac_address(sta_if),
                'connection_status': 'CONNECTED'
            })
        elif mode == 'AP' and success:
            connection_info.update({
                'ip': ip,
                'subnet': '255.255.255.0',
                'gateway': '192.168.4.1',
                'dns': '8.8.8.8',
                'ssid': ap_if.config('essid'),
                'connection_status': 'AP_MODE',
                'clients': NetworkInfoBuilder._get_ap_clients(ap_if)
            })
        else:
            connection_info.update({
                'connection_status': 'DISCONNECTED',
                'ip': '0.0.0.0',
                'ssid': wifi_config.get('SSID', '')
            })
        
        return connection_info
    
    @staticmethod
    def _get_rssi(sta_if):
        """Obter RSSI de forma segura"""
        try:
            return sta_if.status('rssi') if hasattr(sta_if, 'status') else 0
        except:
            return 0
    
    @staticmethod
    def _get_mac_address(sta_if):
        """Obter endereço MAC de forma unificada"""
        try:
            return ubinascii.hexlify(sta_if.config('mac')).decode().upper()
        except:
            return "UNKNOWN"
    
    @staticmethod
    def _get_ap_clients(ap_if):
        """Obter número de clientes AP de forma segura"""
        try:
            return len(ap_if.status('stations')) if hasattr(ap_if, 'status') else 0
        except:
            return 0
    
    @staticmethod
    def get_network_prefix(ip, ap_mode):
        """Obter prefixo da rede de forma unificada"""
        if ap_mode:
            return "192.168.4"
        
        try:
            if ip:
                parts = ip.split(".")
                if len(parts) == 4:
                    return ".".join(parts[:3])
        except Exception:
            pass
        
        return "192.168.1"

class WiFiConnectionManager:
    """Gerenciador reutilizável de conexão WiFi"""
    
    @staticmethod
    def attempt_connection(sta_if, ssid, password, max_retries=3, retry_delay=5):
        """Tentar conexão WiFi de forma reutilizável"""
        logger.info(f"Conectando ao Wi-Fi: {ssid}")
        
        for attempt in range(max_retries):
            try:
                if not sta_if.isconnected():
                    sta_if.connect(ssid, password)
                    
                    # Aguardar conexão
                    for wait in range(20):
                        if sta_if.isconnected():
                            logger.success(f"Conectado ao Wi-Fi! IP: {sta_if.ifconfig()[0]}")
                            return True
                        time.sleep(1)
                    
                    logger.warning(f"Tentativa {attempt + 1}/{max_retries} falhou")
                    time.sleep(retry_delay)
                    
            except Exception as e:
                logger.error(f"Erro na tentativa {attempt + 1}: {e}")
                time.sleep(retry_delay)
        
        return False

class APManager:
    """Gerenciador reutilizável de Access Point"""
    
    @staticmethod
    def setup_ap(ap_if, device_id, wifi_config):
        """Configurar Access Point de forma reutilizável"""
        try:
            ap_ssid_prefix = wifi_config.get('AP_SSID_PREFIX', 'TRASH_AI_')
            ap_ssid = f"{ap_ssid_prefix}{device_id[-4:]}"
            ap_password = wifi_config.get('AP_PASSWORD', 'trashai2024')
            ap_channel = wifi_config.get('AP_CHANNEL', 6)
            
            ap_if.active(True)
            ap_if.config(
                essid=ap_ssid,
                password=ap_password,
                authmode=3,
                channel=ap_channel
            )
            
            # Configurar IP fixo
            ap_if.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '8.8.8.8'))
            
            logger.success(f"AP Configurado - SSID: {ap_ssid}, IP: 192.168.4.1")
            return True, ap_ssid
            
        except Exception as e:
            logger.error(f"Erro ao configurar AP: {e}")
            return False, None

class NetworkStatusUpdater:
    """Atualizador reutilizável de status de rede"""
    
    @staticmethod
    def update_wifi_status(config_mgr, sta_if, wifi_config, connected=True):
        """Atualizar status WiFi na configuração"""
        ifconfig = sta_if.ifconfig()
        wifi_status = {
            'CURRENT_IP': ifconfig[0],
            'GATEWAY': ifconfig[2],
            'SUBNET_MASK': ifconfig[1],
            'DNS': ifconfig[3],
            'LAST_CONNECTED_SSID': wifi_config.get('SSID'),
            'CONNECTION_STATUS': 'CONNECTED' if connected else 'DISCONNECTED',
            'MODE': 'STA'
        }
        
        # Adicionar RSSI se disponível
        if hasattr(sta_if, 'status'):
            wifi_status['RSSI'] = sta_if.status('rssi')
            
        return config_mgr.update_config_section('WiFiConfig', wifi_status)
    
    @staticmethod
    def update_ap_status(config_mgr, ap_ssid, ip='192.168.4.1'):
        """Atualizar status AP na configuração"""
        ap_status = {
            'CURRENT_IP': ip,
            'CONNECTION_STATUS': 'AP_MODE',
            'MODE': 'AP',
            'AP_SSID': ap_ssid
        }
        return config_mgr.update_config_section('WiFiConfig', ap_status)