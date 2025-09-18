from machine import Pin
import time
from config import *
from communication import send_message, get_active_channel

# Global sensor variables
movement_detected = False
movement_detection_time = 0

# Initialize PIR sensor
pir_sensor = Pin(PIR_SENSOR_PIN, Pin.IN)

def detect_movement():
    """Detects movement via PIR sensor and notifies via the active channel"""
    global movement_detected, movement_detection_time
    
    if pir_sensor.value() == 1 and not movement_detected:
        movement_detected = True
        movement_detection_time = time.ticks_ms()
        
        # Get the active channel for the message
        active_channel = get_active_channel()
        
        # Send movement detected message
        send_message(f"{MSG_MOVEMENT_DETECTED}:{PREFIX_CANAL}{active_channel}")
        print(f"INFO: Movement detected (Active channel: {active_channel})")
        
        return True
    
    return False

def get_movement_status():
    """Returns the current PIR sensor status"""
    return {
        'movement_detected': movement_detected,
        'time_since_detection': time.ticks_diff(time.ticks_ms(), movement_detection_time) if movement_detected else 0,
        'sensor_value': pir_sensor.value()
    }