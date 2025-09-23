import machine
import time
import os

def boot_sequence():
    """Sequência de boot simplificada"""
    led = machine.Pin(2, machine.Pin.OUT)
    
    # Pisca LED para indicar boot
    for _ in range(3):
        led.on()
        time.sleep_ms(200)
        led.off()
        time.sleep_ms(200)
    
    print("=" * 40)
    print("  ESP32 SMART TRASH CAN")
    print("=" * 40)
    
    # Verifica arquivos essenciais
    essential_files = ['main.py', 'config.py', 'utils.py']
    for file in essential_files:
        try:
            with open(file, 'r'):
                print(f"✓ {file} encontrado")
        except:
            print(f"✗ {file} não encontrado")
    
    print("Sistema pronto!")
    led.on()  # LED ligado indica sistema pronto

if __name__ == "__main__":
    boot_sequence()