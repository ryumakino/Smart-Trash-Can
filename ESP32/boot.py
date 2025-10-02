# boot.py - Inicialização segura do ESP32
import machine
import time
import gc

def setup_hardware():
    """Configuração inicial do hardware"""
    # Limpar memória
    gc.collect()
    
    # Configurar frequência da CPU (opcional)
    # machine.freq(240000000)  # 240MHz
    
    # Inicializar LED de status
    led = machine.Pin(2, machine.Pin.OUT)
    led.off()  # Desligar LED inicialmente
    
    print("=== ESP32 TRASH AI BOOT ===")
    print(f"CPU Frequency: {machine.freq() // 1000000}MHz")
    print(f"Free memory: {gc.mem_free()} bytes")
    print("Hardware initialized successfully")
    
    return led

def main():
    """Função principal de boot"""
    try:
        led = setup_hardware()
        
        # Piscar LED indicando boot
        for _ in range(3):
            led.on()
            time.sleep(0.1)
            led.off()
            time.sleep(0.1)
            
        print("Boot completed - Starting main application...")
        
    except Exception as e:
        print(f"Boot error: {e}")
        machine.reset()  # Hard reset em caso de falha

if __name__ == '__main__':
    main()