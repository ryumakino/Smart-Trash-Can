from machine import Pin, PWM
import time
from config import *
from communication import send_message, get_active_channel

# Initialize the servo
servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQUENCY)

def angle_to_duty(angle):
    """Convert angle to PWM duty cycle"""
    return int(SERVO_DUTY_MIN + (angle / 180) * SERVO_DUTY_RANGE)

def initialize_servo():
    """Initialize the servo at the neutral position"""
    move_servo_angle(NEUTRAL_POSITION)
    print("INFO: Servo initialized at neutral position")
    send_message(f"{MSG_SERVO_INITIALIZED}:NEUTRAL")

def move_servo(waste_type):
    """Move the servo to the position corresponding to the waste type"""
    if waste_type < 0 or waste_type >= len(SERVO_POSITIONS):
        print("ERROR: Invalid waste type, moving to neutral position")
        move_servo_angle(NEUTRAL_POSITION)
        return False
    
    target_angle = SERVO_POSITIONS[waste_type]
    waste_name = WASTE_TYPES[waste_type]
    
    # Get active communication channel for logging
    active_channel = get_active_channel()
    
    print(f"INFO: Moving servo to {target_angle}° ({waste_name}) via {active_channel}")
    send_message(f"{MSG_SERVO_MOVING}:{PREFIX_TIPO}{waste_type}:{PREFIX_ANGULO}{target_angle}:{PREFIX_CANAL}{active_channel}")
    
    move_servo_angle(target_angle)
    return True

def move_servo_angle(angle):
    """Move servo to a specific angle"""
    # Clamp angle between 0 and 180 degrees
    angle = max(0, min(180, angle))
    
    servo.duty(angle_to_duty(angle))
    time.sleep(SERVO_MOVEMENT_DELAY)
    
    # Confirm movement
    send_message(f"{MSG_SERVO_POSITIONED}:{PREFIX_ANGULO}{angle}")
    
    return angle

def get_servo_status():
    """Return current servo status"""
    return {
        'pin': SERVO_PIN,
        'initialized': True,
        'neutral_position': NEUTRAL_POSITION,
        'waste_positions': SERVO_POSITIONS,
        'frequency': SERVO_FREQUENCY
    }