# services/mqtt_client.py - SERVIDOR ATUALIZADO
import paho.mqtt.client as mqtt
import json
import time
from typing import Dict, Any, Callable
from src.core.base_classes import BaseService

class MQTTClient(BaseService):
    """Cliente MQTT do servidor para comunicação com ESP32"""
    
    def __init__(self):
        super().__init__("MQTTClient")
        self.client = None
        self.message_handlers = {}
        self.connected = False
        
    def _initialize_impl(self) -> bool:
        try:
            from src.config.config_manager import CONFIG_MANAGER
            mqtt_config = CONFIG_MANAGER.get_mqtt_config()
            
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            broker_host = mqtt_config.get("BROKER_HOST", "localhost")
            broker_port = mqtt_config.get("BROKER_PORT", 1883)
            keepalive = mqtt_config.get("KEEPALIVE", 60)
            
            self.client.connect(broker_host, broker_port, keepalive)
            self.client.loop_start()
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao conectar MQTT: {e}")
            return False
    
    def _cleanup_impl(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.logger.info("✅ Conectado ao broker MQTT")
            self._subscribe_esp32_topics()
        else:
            self.logger.error(f"❌ Falha na conexão MQTT: código {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.logger.warning("⚠️ Desconectado do broker MQTT")
    
    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            self.logger.debug(f"📨 MQTT RX: {topic}")
            
            # Encontrar handler para o tópico
            for topic_pattern, handler in self.message_handlers.items():
                if self._topic_matches(topic, topic_pattern):
                    handler(topic, payload)
                    break
            else:
                self.logger.warning(f"📨 Mensagem não tratada: {topic}")
                
        except Exception as e:
            self.logger.error(f"Erro ao processar mensagem MQTT: {e}")
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Verifica se o tópico corresponde ao padrão"""
        if pattern.endswith('#'):
            return topic.startswith(pattern[:-1])
        elif '+' in pattern:
            pattern_parts = pattern.split('/')
            topic_parts = topic.split('/')
            
            if len(pattern_parts) != len(topic_parts):
                return False
            
            for p_part, t_part in zip(pattern_parts, topic_parts):
                if p_part != '+' and p_part != t_part:
                    return False
            return True
        else:
            return topic == pattern
    
    def _subscribe_esp32_topics(self):
        """Inscreve nos tópicos dos dispositivos ESP32"""
        from src.config.config_manager import CONFIG_MANAGER
        mqtt_config = CONFIG_MANAGER.get_mqtt_config()
        topic_prefix = mqtt_config.get("TOPIC_PREFIX", "trashnet")
        
        # Tópicos para receber requisições dos ESP32
        esp32_topics = [
            f"{topic_prefix}/classification/request",           # Requisições genéricas
            f"{topic_prefix}/devices/+/classification/request", # Requisições específicas
            f"{topic_prefix}/+/status",                         # Status dos dispositivos
            f"{topic_prefix}/+/events"                          # Eventos dos dispositivos
        ]
        
        for topic in esp32_topics:
            self.client.subscribe(topic)
            self.logger.info(f"📡 Inscrito no tópico: {topic}")
    
    def register_message_handler(self, topic_pattern: str, handler: Callable):
        """Registra um handler para mensagens de um tópico específico"""
        self.message_handlers[topic_pattern] = handler
        self.logger.info(f"🔄 Handler registrado para: {topic_pattern}")
    
    def publish_to_device(self, device_id: str, subtopic: str, message: Dict[str, Any]):
        """Publica mensagem para um dispositivo ESP32 específico"""
        from src.config.config_manager import CONFIG_MANAGER
        mqtt_config = CONFIG_MANAGER.get_mqtt_config()
        topic_prefix = mqtt_config.get("TOPIC_PREFIX", "trashnet")
        qos = mqtt_config.get("QOS", 1)
        
        topic = f"{topic_prefix}/devices/{device_id}/{subtopic}"
        
        if not self.connected:
            self.logger.warning("⚠️ MQTT não conectado, mensagem não enviada")
            return False
        
        try:
            result = self.client.publish(
                topic, 
                json.dumps(message), 
                qos=qos
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"📤 Publicado para {device_id}: {subtopic}")
                return True
            else:
                self.logger.error(f"❌ Erro ao publicar: código {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Exceção ao publicar: {e}")
            return False
    
    def publish_generic(self, topic: str, message: Dict[str, Any]):
        """Publica mensagem em tópico genérico"""
        if not self.connected:
            self.logger.warning("⚠️ MQTT não conectado, mensagem não enviada")
            return False
        
        try:
            result = self.client.publish(
                topic, 
                json.dumps(message), 
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"📤 Publicado em {topic}")
                return True
            else:
                self.logger.error(f"❌ Erro ao publicar: código {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Exceção ao publicar: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            "connected": self.connected,
            "handlers_registered": len(self.message_handlers)
        })
        return status