from machine import Pin, Timer
import time
from config import PIR_SENSOR_PIN, MOVEMENT_TIMEOUT_MS, MSG_MOVEMENT_DETECTED, PREFIX_CANAL, MSG_TIMEOUT, DEBOUNCE_DELAY_MS
from utils import log_message
from communication import send_message, get_active_channel

# Global sensor variables
pir_sensor = Pin(PIR_SENSOR_PIN, Pin.IN)
movement_timer = Timer(1)
last_movement_time = 0
movement_detected = False

def pir_callback(pin) -> None:
    """
    PIR sensor interrupt callback function.
    
    Args:
        pin: Pin that triggered the interrupt
    """
    global last_movement_time, movement_detected
    
    try:
        if pin.value() == 1:
            movement_detected = True
            last_movement_time = time.ticks_ms()
            
            active_channel = get_active_channel()
            send_message(f"{MSG_MOVEMENT_DETECTED}:{PREFIX_CANAL}{active_channel}")
            log_message("INFO", f"Movement detected (Active channel: {active_channel})")
    except Exception as e:
        log_message("ERROR", f"PIR callback error: {e}")

def initialize_sensor() -> bool:
    """
    Initialize PIR sensor with interrupt.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Set up interrupt on rising edge (movement detected)
        pir_sensor.irq(trigger=Pin.IRQ_RISING, handler=pir_callback)
        log_message("INFO", "PIR sensor initialized with interrupt")
        return True
    except Exception as e:
        log_message("ERROR", f"PIR sensor initialization failed: {e}")
        return False

def detect_movement() -> bool:
    """
    Detect movement via PIR sensor.
    Uses interrupt, so this is just for polling fallback.
    
    Returns:
        bool: True if movement detected, False otherwise
    """
    # Esta função é apenas um fallback para polling
    # A detecção principal é feita via interrupt
    global movement_detected
    return movement_detected

def check_movement_timeout(timer=None) -> None:
    """
    Check for movement timeout.
    Timer callback function.
    """
    global last_movement_time, movement_detected
    
    current_time = time.ticks_ms()
    if (movement_detected and 
        time.ticks_diff(current_time, last_movement_time) > MOVEMENT_TIMEOUT_MS):
        log_message("WARNING", "Movement timeout - no selection made")
        send_message(f"{MSG_TIMEOUT}:NO_SELECTION")
        movement_detected = False

def reset_movement_detection() -> None:
    """
    Reset movement detection flags.
    """
    global movement_detected
    movement_detected = False
    log_message("DEBUG", "Movement detection reset")

def get_movement_status() -> dict:
    """
    Get current PIR sensor status.
    
    Returns:
        dict: Status dictionary
    """
    global last_movement_time, movement_detected
    
    return {
        'movement_detected': movement_detected,
        'time_since_detection': time.ticks_diff(time.ticks_ms(), last_movement_time) if movement_detected else 0,
        'sensor_value': pir_sensor.value(),
        'sensor_pin': PIR_SENSOR_PIN,
        'debounce_delay': DEBOUNCE_DELAY_MS,
        'last_detection_time': last_movement_time
    }

def test_sensor() -> bool:
    """
    Test PIR sensor functionality.
    
    Returns:
        bool: True if test passed, False otherwise
    """
    try:
        log_message("INFO", "Testing PIR sensor...")
        
        # Read current value
        value = pir_sensor.value()
        log_message("INFO", f"PIR sensor value: {value}")
        
        # Test interrupt setup
        original_handler = pir_sensor.irq().handler() if pir_sensor.irq() else None
        
        # Temporary disable interrupt for test
        pir_sensor.irq(handler=None)
        
        # Test direct reading
        test_value = pir_sensor.value()
        log_message("INFO", f"PIR test reading: {test_value}")
        
        # Restore interrupt handler
        if original_handler:
            pir_sensor.irq(trigger=Pin.IRQ_RISING, handler=original_handler)
        else:
            pir_sensor.irq(trigger=Pin.IRQ_RISING, handler=pir_callback)
        
        log_message("INFO", "PIR sensor test completed")
        return True
        
    except Exception as e:
        log_message("ERROR", f"PIR sensor test failed: {e}")
        return False

# Initialize sensor and timeout timer
initialize_sensor()
movement_timer.init(period=1000, mode=Timer.PERIODIC, callback=check_movement_timeout)