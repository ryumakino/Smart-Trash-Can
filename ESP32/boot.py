"""
Boot script for ESP32 Smart Trash Can System.
Runs on MicroPython startup.
"""

import machine
import time
from config import LED_PIN

def main() -> None:
    """Main boot function."""
    print("ESP32 Smart Trash Can Booting...")
    
    # Basic hardware test
    led = machine.Pin(LED_PIN, machine.Pin.OUT)
    for _ in range(3):
        led.on()
        time.sleep_ms(200)
        led.off()
        time.sleep_ms(200)
    
    print("Boot completed. Starting main application...")
    
    # Import and start main application
    import main
    main.main()

# Run main function if this is the main module
if __name__ == "__main__":
    main()