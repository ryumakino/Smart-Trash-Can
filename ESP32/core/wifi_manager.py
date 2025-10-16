# core/wifi_manager.py
import network
import uasyncio as asyncio
import socket
import json
import time
from utils import get_logger

logger = get_logger("WiFiManager")

class WiFiManager:
    def __init__(self, config_methods):
        self.config = config_methods
        self.sta = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)
        self.connected = False
        self.config_mode = False
        
    async def start_ap_mode(self):
        """Inicia modo Access Point para configuração - CORRIGIDO"""
        try:
            # Desativa STA primeiro
            if self.sta.active():
                self.sta.active(False)
            
            # Aguarda um pouco
            await asyncio.sleep(1)
            
            # Ativa o AP
            self.ap.active(True)
            await asyncio.sleep(1)
            
            device_id = self.config['get']('device', 'id')
            ap_ssid = f"{device_id}"[:32]
            
            self.ap.config(essid=ap_ssid)
            await asyncio.sleep(0.5)
            
            self.ap.config(password="config123", authmode=network.AUTH_WPA_WPA2_PSK)
            
            # Aguarda o AP ficar ativo
            timeout = time.time() + 10
            while not self.ap.active() and time.time() < timeout:
                await asyncio.sleep(0.5)
            
            if self.ap.active():
                # Configura IP fixo - método correto
                self.ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '8.8.8.8'))
                self.config_mode = True
                logger.info(f"📡 Modo AP ativo: {ap_ssid} - IP: 192.168.4.1")
                return True
            else:
                logger.error("❌ Falha ao ativar modo AP")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro iniciando AP: {e}")
            import sys
            sys.print_exception(e)
            return False
    
    async def connect_sta(self, ssid, password):
        """Conecta à rede WiFi"""    
        self.sta.active(True)
        self.sta.connect(ssid, password)
        
        for _ in range(5):
            if self.sta.isconnected():
                self.connected = True
                self.config_mode = False
                logger.success(f"✅ Conectado à WiFi: {ssid}")
                logger.info(f"📡 IP: {self.sta.ifconfig()[0]}")
                return True
            await asyncio.sleep(3)
        
        logger.error(f"❌ Falha ao conectar à Wifi: {ssid}")
        self.sta.active(False)
        return False
    
    def is_connected(self):
        return self.sta.isconnected() if self.sta.active() else False
    
    def get_ip(self):
        return self.sta.ifconfig()[0] if self.is_connected() else "192.168.4.1"
    
    async def start_config_server(self):
        """Inicia servidor web para configuração"""
        if not self.config_mode:
            return
        
        logger.info("🖥️ Iniciando servidor de configuração...")
        
        # HTML da página de configuração
        html = """<!DOCTYPE html>
    <html>
    <head>
        <title>Configuração Trash AI</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial; margin: 20px; background: #f5f5f5; }
            .container { max-width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #2980b9; }
            .status { padding: 10px; border-radius: 5px; margin: 10px 0; text-align: center; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .info { background: #d1ecf1; color: #0c5460; }
            .section { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #3498db; }
            .section h3 { margin-top: 0; color: #2c3e50; }
            .form-row { display: flex; gap: 10px; }
            .form-row .form-group { flex: 1; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 Configuração Trash AI</h1>
            <div class="status info">
                Dispositivo: %DEVICE_ID%<br>
                Configure todos os parâmetros do sistema
            </div>
            
            <form method="post" action="/configure">
                <div class="section">
                    <h3>📱 Informações do Dispositivo</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>ID do Dispositivo:</label>
                            <input type="text" name="device_id" value="%DEVICE_ID%" readonly style="background: #f0f0f0;">
                        </div>
                        <div class="form-group">
                            <label>Tipo:</label>
                            <select name="device_type">
                                <option value="TRASH_CAN">Lixeira</option>
                                <option value="RECYCLING_STATION">Estação de Reciclagem</option>
                                <option value="COMPOST_BIN">Composteira</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Nome do Dispositivo:</label>
                        <input type="text" name="device_name" placeholder="Lixeira Inteligente - ESP32" value="%DEVICE_NAME%">
                    </div>
                    <div class="form-group">
                        <label>Localização:</label>
                        <input type="text" name="device_location" placeholder="Sala de Reuniões" value="%DEVICE_LOCATION%">
                    </div>
                </div>

                <div class="section">
                    <h3>📶 Configuração WiFi</h3>
                    <div class="form-group">
                        <label>Rede WiFi (SSID):</label>
                        <input type="text" name="ssid" required placeholder="Nome da sua rede" value="%WIFI_SSID%">
                    </div>
                    
                    <div class="form-group">
                        <label>Senha WiFi:</label>
                        <input type="password" name="password" required placeholder="Senha da rede" value="%WIFI_PASSWORD%">
                    </div>
                    
                    <div class="form-group">
                        <label>Tentativas de Conexão:</label>
                        <input type="number" name="wifi_max_retries" min="1" max="10" value="%WIFI_RETRIES%">
                    </div>
                </div>

                <div class="section">
                    <h3>☁️ Configuração MQTT</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Broker MQTT:</label>
                            <input type="text" name="mqtt_broker" placeholder="broker.hivemq.com" value="%MQTT_BROKER%">
                        </div>
                        <div class="form-group">
                            <label>Porta:</label>
                            <input type="number" name="mqtt_port" min="1" max="65535" value="%MQTT_PORT%">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Tópico Base:</label>
                        <input type="text" name="mqtt_topic_base" placeholder="trashnet" value="%MQTT_TOPIC%">
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>QoS:</label>
                            <select name="mqtt_qos">
                                <option value="0">0 - No máximo uma vez</option>
                                <option value="1">1 - Pelo menos uma vez</option>
                                <option value="2">2 - Exatamente uma vez</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Keep Alive (s):</label>
                            <input type="number" name="mqtt_keepalive" min="10" max="300" value="%MQTT_KEEPALIVE%">
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h3>⚙️ Configuração do Servo</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Pino do Servo:</label>
                            <input type="number" name="servo_pin" min="0" max="40" value="%SERVO_PIN%">
                        </div>
                        <div class="form-group">
                            <label>Frequência (Hz):</label>
                            <input type="number" name="servo_freq" min="1" max="1000" value="%SERVO_FREQ%">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>Duty Mínimo:</label>
                            <input type="number" name="servo_min_duty" min="0" max="1000" value="%SERVO_MIN_DUTY%">
                        </div>
                        <div class="form-group">
                            <label>Duty Máximo:</label>
                            <input type="number" name="servo_max_duty" min="0" max="1000" value="%SERVO_MAX_DUTY%">
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h3>📊 Configuração de Sensores</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Pino do Sensor IR:</label>
                            <input type="number" name="sensor_ir_pin" min="0" max="40" value="%SENSOR_IR_PIN%">
                        </div>
                        <div class="form-group">
                            <label>Intervalo de Verificação (s):</label>
                            <input type="number" name="sensor_check_interval" step="0.1" min="0.1" max="10" value="%SENSOR_CHECK_INTERVAL%">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Tempo de Espera entre Movimentos (s):</label>
                        <input type="number" name="sensor_cooldown" min="1" max="60" value="%SENSOR_COOLDOWN%">
                    </div>
                </div>

                <div class="section">
                    <h3>💡 Configuração do Sistema</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Pino do LED:</label>
                            <input type="number" name="system_led_pin" min="0" max="40" value="%SYSTEM_LED_PIN%">
                        </div>
                        <div class="form-group">
                            <label>Intervalo Health Check (s):</label>
                            <input type="number" name="system_health_interval" min="5" max="300" value="%SYSTEM_HEALTH_INTERVAL%">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>Timeout Classificação (s):</label>
                        <input type="number" name="system_classification_timeout" min="5" max="60" value="%SYSTEM_CLASSIFICATION_TIMEOUT%">
                    </div>
                </div>

                <button type="submit">💾 Salvar Configuração Completa</button>
            </form>
            
            <div style="margin-top: 20px; text-align: center; font-size: 12px; color: #666;">
                Após salvar, o dispositivo reiniciará e aplicará as novas configurações.
            </div>
        </div>
    </body>
    </html>"""
        
        # Substitui placeholders com valores atuais
        html = html.replace('%DEVICE_ID%', self.config['get']('device', 'id', 'TRASH_AI_ESP32_001'))
        html = html.replace('%DEVICE_NAME%', self.config['get']('device', 'name', 'Lixeira Inteligente - ESP32'))
        html = html.replace('%DEVICE_LOCATION%', self.config['get']('device', 'location', 'Sala de Reuniões'))
        html = html.replace('%WIFI_SSID%', self.config['get']('wifi', 'ssid', ''))
        html = html.replace('%WIFI_PASSWORD%', self.config['get']('wifi', 'password', ''))
        html = html.replace('%WIFI_RETRIES%', str(self.config['get']('wifi', 'max_retries', 3)))
        html = html.replace('%MQTT_BROKER%', self.config['get']('mqtt', 'broker', 'broker.hivemq.com'))
        html = html.replace('%MQTT_PORT%', str(self.config['get']('mqtt', 'port', 1883)))
        html = html.replace('%MQTT_TOPIC%', self.config['get']('mqtt', 'topic_base', 'trashnet'))
        html = html.replace('%MQTT_KEEPALIVE%', str(self.config['get']('mqtt', 'keepalive', 60)))
        html = html.replace('%SERVO_PIN%', str(self.config['get']('servo', 'pin', 18)))
        html = html.replace('%SERVO_FREQ%', str(self.config['get']('servo', 'freq', 50)))
        html = html.replace('%SERVO_MIN_DUTY%', str(self.config['get']('servo', 'min_duty', 40)))
        html = html.replace('%SERVO_MAX_DUTY%', str(self.config['get']('servo', 'max_duty', 115)))
        html = html.replace('%SENSOR_IR_PIN%', str(self.config['get']('sensors', 'ir_pin', 34)))
        html = html.replace('%SENSOR_CHECK_INTERVAL%', str(self.config['get']('sensors', 'check_interval', 0.1)))
        html = html.replace('%SENSOR_COOLDOWN%', str(self.config['get']('sensors', 'movement_cooldown', 10)))
        html = html.replace('%SYSTEM_LED_PIN%', str(self.config['get']('system', 'led_pin', 2)))
        html = html.replace('%SYSTEM_HEALTH_INTERVAL%', str(self.config['get']('system', 'health_check_interval', 30)))
        html = html.replace('%SYSTEM_CLASSIFICATION_TIMEOUT%', str(self.config['get']('system', 'classification_timeout', 30)))
        
        # Inicia servidor
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(5)
        s.setblocking(False)
        
        logger.info(f"🌐 Servidor config ativo em http://{self.get_ip()}")
        
        while self.config_mode:
            try:
                try:
                    cl, addr = s.accept()
                except OSError as e:
                    if e.args[0] == 11:
                        await asyncio.sleep(0.1)
                        continue
                    else:
                        raise
                
                request = cl.recv(1024).decode()
                logger.debug(f"📨 Request: {request.splitlines()[0] if request else 'Empty'}")
                
                # Processa requisições
                if 'POST /configure' in request:
                    try:
                        # Lê toda a requisição primeiro
                        full_request = request
                        while True:
                            try:
                                part = cl.recv(1024).decode()
                                if not part:
                                    break
                                full_request += part
                            except:
                                break
                        
                        # Encontra o corpo do POST
                        if '\r\n\r\n' in full_request:
                            headers, body = full_request.split('\r\n\r\n', 1)
                        else:
                            body = ""
                        
                        logger.debug(f"📦 Body recebido: {body}")
                        
                        # Processa os parâmetros
                        params = {}
                        if body:
                            for pair in body.split('&'):
                                if '=' in pair:
                                    key, value = pair.split('=', 1)
                                    # Decodificação básica
                                    value = value.replace('+', ' ')
                                    params[key] = value
                        
                        logger.info(f"📝 Dados processados: {len(params)} parâmetros")
                        
                        # Verifica se os dados WiFi estão presentes
                        if not params.get('ssid') or not params.get('password'):
                            logger.error("❌ Dados WiFi incompletos no formulário")
                            response_html = """
                            <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                                <h1>❌ Erro no Formulário</h1>
                                <p>SSID e senha WiFi são obrigatórios.</p>
                                <p><a href="/">Voltar</a></p>
                            </body></html>
                            """
                            cl.send('HTTP/1.1 400 Bad Request\r\nContent-type: text/html\r\n\r\n')
                            cl.send(response_html)
                            cl.close()
                            continue
                        
                        # Salva configuração completa
                        success = await self._save_complete_config(params)
                        
                        # Resposta
                        response_html = """
                        <html>
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>Configuração Salva</title>
                            <style>
                                body { font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5; }
                                .container { max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                                .success { color: #155724; background: #d4edda; padding: 15px; border-radius: 5px; }
                                .error { color: #721c24; background: #f8d7da; padding: 15px; border-radius: 5px; }
                                .config-summary { text-align: left; background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h1>%MESSAGE%</h1>
                                <div class="%CLASS%">
                                    <p>%DETAILS%</p>
                                    <div class="config-summary">
                                        <p><strong>Configurações Aplicadas:</strong></p>
                                        <p>📱 Dispositivo: %DEVICE_NAME%</p>
                                        <p>📶 WiFi: %SSID%</p>
                                        <p>☁️ MQTT: %MQTT_BROKER%:%MQTT_PORT%</p>
                                        <p>⚙️ Servo: Pino %SERVO_PIN%</p>
                                    </div>
                                    <p><small>%ACTION%</small></p>
                                </div>
                            </div>
                        </body>
                        </html>
                        """
                        
                        if success:
                            response_html = response_html.replace('%MESSAGE%', '✅ Configuração Salva!')
                            response_html = response_html.replace('%CLASS%', 'success')
                            response_html = response_html.replace('%DETAILS%', 'Todas as configurações foram salvas com sucesso.')
                            response_html = response_html.replace('%DEVICE_NAME%', params.get('device_name', ''))
                            response_html = response_html.replace('%SSID%', params.get('ssid', ''))
                            response_html = response_html.replace('%MQTT_BROKER%', params.get('mqtt_broker', ''))
                            response_html = response_html.replace('%MQTT_PORT%', params.get('mqtt_port', ''))
                            response_html = response_html.replace('%SERVO_PIN%', params.get('servo_pin', ''))
                            response_html = response_html.replace('%ACTION%', 'O dispositivo irá reiniciar em 5 segundos...')
                        else:
                            response_html = response_html.replace('%MESSAGE%', '❌ Erro ao Salvar')
                            response_html = response_html.replace('%CLASS%', 'error')
                            response_html = response_html.replace('%DETAILS%', 'Erro ao salvar configuração completa.')
                            response_html = response_html.replace('%ACTION%', '<a href="/">Tentar novamente</a>')
                        
                        cl.send('HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n')
                        cl.send(response_html)
                        cl.close()
                        
                        # Reinicia apenas se salvou com sucesso
                        if success:
                            logger.info("🔄 Reiniciando em 5 segundos para aplicar novas configurações...")
                            await asyncio.sleep(5)
                            import machine
                            machine.reset()
                        
                    except Exception as e:
                        logger.error(f"❌ Erro processando POST: {e}")
                        error_response = """
                        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                            <h1>❌ Erro no Servidor</h1>
                            <p>Erro interno do servidor: %ERROR%</p>
                            <p><a href="/">Voltar</a></p>
                        </body></html>
                        """.replace('%ERROR%', str(e))
                        cl.send('HTTP/1.1 500 Internal Server Error\r\nContent-type: text/html\r\n\r\n')
                        cl.send(error_response)
                        cl.close()
                
                else:
                    # Serve página HTML normal
                    cl.send('HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n')
                    cl.send(html)
                    cl.close()
                    
            except Exception as e:
                logger.error(f"❌ Erro servidor: {e}")
                await asyncio.sleep(1)
        
        s.close()


    async def _save_complete_config(self, params):
        """Salva configuração completa - CORRIGIDO para usar config_manager"""
        try:
            # Dispositivo
            if params.get('device_name'):
                self.config['set']('device', 'name', value=params['device_name'])
            if params.get('device_type'):
                self.config['set']('device', 'type', value=params['device_type'])
            if params.get('device_location'):
                self.config['set']('device', 'location', value=params['device_location'])
            
            # WiFi
            self.config['set']('wifi', 'ssid', value=params.get('ssid', ''))
            self.config['set']('wifi', 'password', value=params.get('password', ''))
            if params.get('wifi_max_retries'):
                self.config['set']('wifi', 'max_retries', value=int(params['wifi_max_retries']))
            
            # MQTT
            if params.get('mqtt_broker'):
                self.config['set']('mqtt', 'broker', value=params['mqtt_broker'])
            if params.get('mqtt_port'):
                self.config['set']('mqtt', 'port', value=int(params['mqtt_port']))
            if params.get('mqtt_topic_base'):
                self.config['set']('mqtt', 'topic_base', value=params['mqtt_topic_base'])
            if params.get('mqtt_qos'):
                self.config['set']('mqtt', 'qos', value=int(params['mqtt_qos']))
            if params.get('mqtt_keepalive'):
                self.config['set']('mqtt', 'keepalive', value=int(params['mqtt_keepalive']))
            
            # Servo
            if params.get('servo_pin'):
                self.config['set']('servo', 'pin', value=int(params['servo_pin']))
            if params.get('servo_freq'):
                self.config['set']('servo', 'freq', value=int(params['servo_freq']))
            if params.get('servo_min_duty'):
                self.config['set']('servo', 'min_duty', value=int(params['servo_min_duty']))
            if params.get('servo_max_duty'):
                self.config['set']('servo', 'max_duty', value=int(params['servo_max_duty']))
            
            # Sensores
            if params.get('sensor_ir_pin'):
                self.config['set']('sensors', 'ir_pin', value=int(params['sensor_ir_pin']))
            if params.get('sensor_check_interval'):
                self.config['set']('sensors', 'check_interval', value=float(params['sensor_check_interval']))
            if params.get('sensor_cooldown'):
                self.config['set']('sensors', 'movement_cooldown', value=int(params['sensor_cooldown']))
            
            # Sistema
            if params.get('system_led_pin'):
                self.config['set']('system', 'led_pin', value=int(params['system_led_pin']))
            if params.get('system_health_interval'):
                self.config['set']('system', 'health_check_interval', value=int(params['system_health_interval']))
            if params.get('system_classification_timeout'):
                self.config['set']('system', 'classification_timeout', value=int(params['system_classification_timeout']))
            
            logger.info("📝 Configuração completa atualizada")
            
            # Salva no arquivo usando config_manager
            if self.config_save():
                logger.success("✅ Configuração completa salva com sucesso")
                return True
            else:
                logger.error("❌ Erro salvando configuração completa")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro salvando configuração completa: {e}")
            import sys
            sys.print_exception(e)
            return False

    def config_save(self):
        """Salva configuração - compatibilidade com config_manager"""
        try:
            # Importa e usa o config_save do config_manager
            from config_manager import config_save
            return config_save()
        except Exception as e:
            logger.error(f"❌ Erro no config_save: {e}")
            return False
    
    async def auto_connect(self):
        """Tenta conectar automaticamente ou inicia modo configuração (AP)"""
        ssid = self.config['get']('wifi', 'ssid')
        password = self.config['get']('wifi', 'password')

        if not ssid or not password:
            logger.warning("❌ Credenciais WiFi não configuradas — iniciando modo AP")
            if await self.start_ap_mode():
                asyncio.create_task(self.start_config_server())
                return False
            return False

        logger.info(f"📡 Tentando conectar à WiFi: {ssid}")
        if await self.connect_sta(ssid, password):
            return True

        # Se falhar conexão STA → inicia AP
        logger.warning("⚠️ Falha ao conectar à Wifi — iniciando modo AP")
        if await self.start_ap_mode():
            asyncio.create_task(self.start_config_server())
            return False

        logger.error("❌ Falha ao iniciar modo AP de configuração")
        return False