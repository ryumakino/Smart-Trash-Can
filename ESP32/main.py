from esp32_messenger import ESP32Messenger
from utils import log_info, log_error, log_success, log_warning
import time
import gc

def main():
    """Função principal do sistema ESP32"""
    log_info("Iniciando sistema de classificação de resíduos ESP32...")
    
    try:
        # Inicializa o sistema de comunicação
        esp = ESP32Messenger()
        esp.start()
        
        log_success("Sistema ESP32 inicializado com sucesso!")
        log_info("Aguardando comandos do PC...")
        
        # Loop principal
        while True:
            # Verifica status da conexão periodicamente
            esp.check_connection_status()
            
            # Coleta de lixo para otimização de memória
            if gc.mem_free() < 10000:  # Menos de 10KB livres
                gc.collect()
                log_info(f"Memória liberada. Livre: {gc.mem_free()} bytes")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        log_info("Encerramento solicitado pelo usuário")
    except Exception as e:
        log_error(f"Erro crítico no sistema: {e}")
    finally:
        # Limpeza final
        if 'esp' in locals():
            esp.stop()
        log_info("Sistema ESP32 encerrado")

if __name__ == "__main__":
    main()