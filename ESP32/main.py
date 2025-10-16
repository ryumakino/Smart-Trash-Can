# main.py - VERSÃO COMPLETA E CORRIGIDA PARA MICROPYTHON ESP32
import uasyncio as asyncio
import time
import gc
import machine
import sys
import os

# ========== IMPORTAÇÕES ROBUSTAS COM FALLBACK ==========
try:
    from config_manager import config_init, config_get, config_get_all, config_set
    print("✅ config_manager importado")
except ImportError as e:
    print(f"❌ Erro importando config_manager: {e}")
    # Fallback mínimo para config_manager
    _config_data = {}
    
    def config_init(filename='config.json'):
        global _config_data
        try:
            with open(filename, 'r') as f:
                import ujson as json
                _config_data = json.load(f)
            return _config_data
        except:
            _config_data = {
                "device": {"id": "TRASH_AI_ESP32", "name": "Lixeira Inteligente"},
                "wifi": {"ssid": "", "password": ""},
                "mqtt": {"broker": "broker.hivemq.com", "port": 1883},
                "servo": {"pin": 18, "min_duty": 40, "max_duty": 115},
                "sensors": {"ir_pin": 34},
                "system": {"led_pin": 2}
            }
            return _config_data
    
    def config_get(*keys, default=None):
        value = _config_data
        try:
            for key in keys:
                value = value[key]
            return value
        except:
            return default
    
    def config_get_all():
        return _config_data
    
    def config_set(*keys, value):
        global _config_data
        if len(keys) == 0:
            return False
        config_level = _config_data
        for key in keys[:-1]:
            if key not in config_level:
                config_level[key] = {}
            config_level = config_level[key]
        config_level[keys[-1]] = value
        return True

try:
    from hardware_manager import HardwareManager
    print("✅ hardware_manager importado")
except ImportError as e:
    print(f"❌ Erro importando hardware_manager: {e}")
    HardwareManager = None

try:
    from mqtt_client import MQTTManager, MQTTMessageHandler
    print("✅ mqtt_client importado")
except ImportError as e:
    print(f"❌ Erro importando mqtt_client: {e}")
    MQTTManager = None
    MQTTMessageHandler = None

try:
    from wifi_manager import WiFiManager
    print("✅ wifi_manager importado")
except ImportError as e:
    print(f"❌ Erro importando wifi_manager: {e}")
    WiFiManager = None

try:
    from utils import get_logger
    print("✅ utils importado")
except ImportError as e:
    print(f"❌ Erro importando utils: {e}")
    # Fallback para logger
    def get_logger(name):
        class SimpleLogger:
            def __init__(self, name): 
                self.name = name
            def _log(self, level, msg): 
                timestamp = time.time()
                print(f"[{level}][{self.name}][{timestamp:.0f}] {msg}")
            def debug(self, msg): self._log("DEBUG", msg)
            def info(self, msg): self._log("INFO", msg)
            def warning(self, msg): self._log("WARN", msg)
            def error(self, msg): self._log("ERROR", msg)
            def success(self, msg): self._log("SUCCESS", msg)
        return SimpleLogger(name)

# ========== CONFIGURAÇÃO SIMPLES ==========
class SimpleConfig:
    """Wrapper simples para o config_manager"""
    def get(self, *args, **kwargs):
        return config_get(*args, **kwargs)
    
    def get_all(self):
        return config_get_all()
    
    def set(self, *args, **kwargs):
        return config_set(*args, **kwargs)

# ========== SISTEMA PRINCIPAL ==========
class TrashAISystem:
    """Sistema principal otimizado para MicroPython ESP32"""
    
    def __init__(self):
        self.running = False
        self.tasks = []
        self.start_time = 0
        
        # Gerenciadores - inicialização tardia
        self.config = None
        self.wifi = None
        self.hardware = None
        self.mqtt = None
        self.message_handler = None
        
        # Estado do sistema
        self.device_info = {}
        self.last_status_sent = 0
        self.status_interval = 30
        self.last_movement_time = 0
        self.movement_cooldown = 10
        
        # Resultados de classificação
        self.last_classification = None
        self.waiting_classification = False
        
        # Status de inicialização
        self.initialized = False
        
        # Logger
        self.logger = get_logger("TrashAI")
    
    async def initialize(self):
        """Inicialização simplificada e robusta"""
        self.logger.info("🚀 Inicializando Trash AI System - MicroPython")
        
        try:
            # 1. Inicializar configuração primeiro
            config_init()
            self.config = SimpleConfig()
            self.logger.success("✅ Configuração carregada")
            
            # 2. Informações do dispositivo
            self.device_info = {
                'device_id': self.config.get('device', 'id', 'TRASH_AI_001'),
                'device_name': self.config.get('device', 'name', 'Lixeira Inteligente'),
                'device_type': 'TRASH_CAN',
                'firmware_version': '2.0.0',
                'first_seen': time.time()
            }
            
            # 3. Conectar WiFi - CORREÇÃO APLICADA AQUI
            if WiFiManager:
                # Criar dicionário com métodos compatíveis para WiFiManager
                config_methods = {
                    'get': self.config.get,
                    'set': self.config.set
                }
                self.wifi = WiFiManager(config_methods)
                wifi_connected = await self.wifi.auto_connect()
            else:
                self.logger.error("❌ WiFiManager não disponível")
                wifi_connected = False
            
            if not wifi_connected:
                self.logger.info("🔧 Modo configuração ativo - conecte-se ao AP")
                return True
            
            self.logger.success("✅ WiFi conectado")
            
            # 4. Inicializar hardware
            if HardwareManager:
                self.hardware = HardwareManager(self.config)
                self.logger.success("✅ Hardware inicializado")
            else:
                self.logger.error("❌ HardwareManager não disponível")
                self.hardware = None
            
            # 5. Conectar MQTT (se disponível)
            if MQTTManager and MQTTMessageHandler:
                try:
                    self.mqtt = MQTTManager(self.config)
                    self.message_handler = MQTTMessageHandler(self.hardware, self)
                    self.mqtt.message_handler = self.message_handler.handle_message
                    await self.mqtt.connect()
                except Exception as e:
                    self.logger.error(f"❌ MQTT falhou: {e}")
                    self.mqtt = None
            else:
                self.logger.warning("⚠️ MQTT não disponível")
                self.mqtt = None
            
            self.initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Falha crítica na inicialização: {e}")
            import sys
            sys.print_exception(e)
            return False
    
    async def start_services(self):
        """Inicia serviços em background"""
        if not self.hardware:
            self.logger.warning("⚠️ Hardware não disponível para serviços")
            return
            
        try:
            # 1. Monitoramento IR Sensor
            ir_sensor = self.hardware.get_component('ir_sensor')
            if ir_sensor and ir_sensor.available:
                ir_sensor.callback = self.on_movement_detected
                self.tasks.append(asyncio.create_task(ir_sensor.start_monitoring()))
                self.logger.info("✅ Monitoramento IR ativado")
            else:
                self.logger.warning("⚠️ Sensor IR não disponível")
            
            # 2. Health monitor
            self.tasks.append(asyncio.create_task(self._health_monitor()))
            self.logger.info("✅ Health monitor ativado")
            
            # 3. Manutenção MQTT
            if self.mqtt:
                self.tasks.append(asyncio.create_task(self._mqtt_maintenance()))
                self.logger.info("✅ Manutenção MQTT ativada")
            
        except Exception as e:
            self.logger.error(f"❌ Erro iniciando serviços: {e}")
    
    async def _health_monitor(self):
        """Monitora saúde do sistema"""
        cycle = 0
        while self.running:
            try:
                cycle += 1
                
                # Coleta de lixo a cada 10 ciclos
                if cycle % 10 == 0:
                    gc.collect()
                
                # Log de memória a cada 30 ciclos
                if cycle % 30 == 0:
                    self.logger.info(f"🧠 Memória livre: {gc.mem_free()} bytes")
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"❌ Erro health monitor: {e}")
                await asyncio.sleep(10)
    
    async def _mqtt_maintenance(self):
        """Manutenção da conexão MQTT"""
        while self.running:
            try:
                if self.mqtt and not self.mqtt.connected:
                    self.logger.warning("🔌 MQTT desconectado, tentando reconectar...")
                    await self.mqtt.connect()
                
                await asyncio.sleep(10)
                
            except Exception as e:
                self.logger.error(f"❌ Erro manutenção MQTT: {e}")
                await asyncio.sleep(30)
    
    async def on_movement_detected(self):
        """Callback quando movimento é detectado"""
        self.logger.info("🚨 Movimento detectado! Solicitando classificação...")
        
        # Cooldown para evitar múltiplas detecções
        current_time = time.time()
        if current_time - self.last_movement_time < self.movement_cooldown:
            self.logger.info("⏳ Em cooldown, ignorando detecção")
            return
        
        self.last_movement_time = current_time
        
        # Publicar evento e solicitar classificação
        await self.publish_event('movement_detected')
        await self.request_classification()
    
    async def publish_event(self, event_type, data=None):
        """Publica evento via MQTT"""
        if not self.mqtt or not self.mqtt.connected:
            return
        
        try:
            event = {
                'type': event_type,
                'timestamp': time.time(),
                'device_id': self.device_info.get('device_id', 'unknown')
            }
            
            if data:
                event.update(data)
            
            await self.mqtt.publish('events', event)
            self.logger.info(f"📢 Evento publicado: {event_type}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro publicando evento: {e}")
    
    async def request_classification(self):
        """Solicita classificação ao servidor"""
        if not self.mqtt or not self.mqtt.connected:
            self.logger.error("❌ MQTT não disponível para classificação")
            return False
        
        if self.waiting_classification:
            self.logger.info("⏳ Já aguardando classificação...")
            return False
        
        try:
            self.waiting_classification = True
            
            classification_request = {
                'action': 'classify',
                'device_id': self.device_info.get('device_id', 'unknown'),
                'device_name': self.device_info.get('device_name', 'unknown'),
                'timestamp': time.time(),
                'request_id': str(time.time())
            }
            
            success = await self.mqtt.publish_to_server('classification/request', classification_request)
            
            if success:
                self.logger.info("📤 Requisição de classificação enviada")
                await self.publish_event('classification_requested')
                
                # Timeout de classificação
                asyncio.create_task(self._classification_timeout())
                return True
            else:
                self.logger.error("❌ Falha ao enviar requisição")
                self.waiting_classification = False
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erro solicitando classificação: {e}")
            self.waiting_classification = False
            return False
    
    async def _classification_timeout(self):
        """Timeout para classificação pendente"""
        await asyncio.sleep(30)  # 30 segundos de timeout
        
        if self.waiting_classification:
            self.logger.warning("⏰ Timeout de classificação")
            self.waiting_classification = False
            await self.publish_event('classification_timeout')
    
    async def process_classification_result(self, waste_type):
        """Processa resultado da classificação"""
        try:
            self.logger.info(f"🎯 Classificação recebida: {waste_type}")
            
            self.last_classification = waste_type
            self.waiting_classification = False
            
            # Mover servo para posição correspondente
            if self.hardware:
                servo = self.hardware.get_component('servo')
                if servo and servo.available:
                    waste_types = self.config.get('servo', 'waste_types', ['Repouso', 'Plástico', 'Papel', 'Metal', 'Vidro'])
                    
                    if waste_type in waste_types:
                        waste_index = waste_types.index(waste_type)
                        success = servo.move_to_waste_type(waste_index)
                        
                        if success:
                            self.logger.success(f"✅ Servo movido para: {waste_type}")
                            await self.publish_event('servo_moved', {'waste_type': waste_type, 'position': waste_index})
                        else:
                            self.logger.error(f"❌ Falha ao mover servo para: {waste_type}")
                    else:
                        self.logger.warning(f"⚠️ Tipo de lixo desconhecido: {waste_type}")
            
            await self.publish_event('classification_completed', {'waste_type': waste_type})
            
        except Exception as e:
            self.logger.error(f"❌ Erro processando classificação: {e}")
            self.waiting_classification = False
    
    async def run(self):
        """Loop principal do sistema"""
        self.start_time = time.time()
        self.running = True
        
        self.logger.info("🎯 Iniciando sistema Trash AI...")
        
        # Inicialização
        if not await self.initialize():
            self.logger.error("❌ Falha crítica na inicialização")
            await self.stop()
            return
        
        # Modo configuração - aguardar conexão WiFi
        if hasattr(self, 'wifi') and self.wifi and not self.wifi.is_connected():
            self.logger.info("🔄 Aguardando configuração WiFi via AP...")
            
            # Manter modo configuração até conectar
            while self.running and not self.wifi.is_connected():
                await asyncio.sleep(2)
            
            # Se conectou, reinicializar hardware
            if self.wifi.is_connected():
                self.logger.success("✅ WiFi conectado! Reinicializando serviços...")
                try:
                    if HardwareManager:
                        self.hardware = HardwareManager(self.config)
                    
                    # Tentar MQTT novamente
                    if not self.mqtt and MQTTManager:
                        try:
                            self.mqtt = MQTTManager(self.config)
                            self.message_handler = MQTTMessageHandler(self.hardware, self)
                            self.mqtt.message_handler = self.message_handler.handle_message
                            await self.mqtt.connect()
                        except Exception as e:
                            self.logger.error(f"❌ MQTT ainda falhou: {e}")
                    
                    await self.start_services()
                except Exception as e:
                    self.logger.error(f"❌ Erro reinicializando: {e}")
        
        else:
            # Iniciar serviços normais
            await self.start_services()
        
        self.logger.success("✅ Sistema Trash AI em execução")
        
        # Loop principal simplificado
        cycle = 0
        while self.running:
            try:
                cycle += 1
                
                # Coleta de lixo periódica
                if cycle % 120 == 0:  # A cada ~60 segundos
                    gc.collect()
                    self.logger.debug("🧹 Coleta de lixo executada")
                    cycle = 0
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"❌ Erro loop principal: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Para o sistema graciosamente"""
        self.logger.info("🛑 Parando sistema...")
        self.running = False
        
        # Cancela tasks
        for task in self.tasks:
            try:
                if not task.done():
                    task.cancel()
            except:
                pass
        
        # Desconecta MQTT
        if self.mqtt:
            try:
                self.mqtt.disconnect()
            except:
                pass
        
        # Limpa hardware
        if self.hardware:
            try:
                self.hardware.cleanup()
            except:
                pass
        
        self.logger.info("✅ Sistema parado")
        await asyncio.sleep(1)

# ========== FUNÇÃO PRINCIPAL ==========
async def main():
    """Função principal da aplicação"""
    system = TrashAISystem()
    
    try:
        await system.run()
    except KeyboardInterrupt:
        system.logger.info("⏹️ Interrompido pelo usuário")
    except Exception as e:
        system.logger.error(f"💥 Erro fatal: {e}")
        import sys
        sys.print_exception(e)
    finally:
        await system.stop()

# ========== PONTO DE ENTRADA ROBUSTO ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🗑️  TRASH AI SYSTEM - ESP32 MicroPython")
    print("=" * 50)
    
    # Verificação inicial do sistema
    print("🔍 Verificando sistema...")
    print(f"📦 Memória livre: {gc.mem_free()} bytes")
    print(f"🐍 Python: {sys.implementation.name} {sys.version}")
    
    try:
        # Coleta de lixo inicial
        gc.collect()
        initial_mem = gc.mem_free()
        print(f"🧹 Memória após limpeza: {initial_mem} bytes")
        
        # Verifica se temos memória suficiente
        if initial_mem < 20000:
            print("❌ Memória insuficiente para iniciar sistema")
            print("🔄 Reiniciando em 5 segundos...")
            time.sleep(5)
            machine.reset()
        
        # Inicia o sistema principal
        print("🚀 Iniciando sistema principal...")
        asyncio.run(main())
        
    except Exception as e:
        print(f"💥 ERRO CRÍTICO: {e}")
        import sys
        sys.print_exception(e)
        
        # Reset de emergência após 10 segundos
        print("🔄 Reset de emergência em 10 segundos...")
        time.sleep(10)
        machine.reset()