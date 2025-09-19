# boot.py - Versão simplificada e funcional
import machine
import time
import os

def main():
    print("==========================================")
    print("       ESP32 SMART TRASH CAN SYSTEM")
    print("==========================================")
    
    # Teste básico do hardware - LED
    led = machine.Pin(2, machine.Pin.OUT)
    for i in range(3):
        led.on()
        time.sleep_ms(200)
        led.off()
        time.sleep_ms(200)
    
    print("Boot completed. Checking files...")
    
    # Listar arquivos Python
    py_files = [f for f in os.listdir() if f.endswith('.py')]
    print(f"Found {len(py_files)} Python files")
    
    # Carregar main application
    if 'main.py' in py_files:
        try:
            print("Starting main application...")
            with open('main.py') as f:
                exec(f.read(), globals())   # roda o conteúdo do main.py
        except Exception as e:
            print(f"Error starting main: {e}")
    else:
        print("main.py not found!")

# Executar
main()