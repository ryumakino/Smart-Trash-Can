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
    
    print("Boot completed. Starting main.py...")

    try:
        import main
    except Exception as e:
        print("Error importing main.py:", e)