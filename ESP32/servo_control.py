from machine import Pin, PWM
import time
from config import (
    SERVO_PIN,
    SERVO_FREQUENCY,
    SERVO_DUTY_MIN,
    SERVO_DUTY_MAX,
    SERVO_DUTY_RANGE,
    NEUTRAL_POSITION,
    SERVO_POSITIONS,
    WASTE_TYPES,
    SERVO_MOVEMENT_DELAY,
    MSG_SERVO_INITIALIZED,
    MSG_SERVO_MOVING,
    MSG_SERVO_POSITIONED,
    MSG_ERROR,
    PREFIX_TIPO,
    PREFIX_ANGULO,
    PREFIX_CANAL
)
from utils import log_message, safe_int, clamp, map_value
from communication import send_message, get_active_channel

# Initialize the servo
servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQUENCY)

def angle_to_duty(angle: int) -> int:
    """
    Convert angle to PWM duty cycle.
    
    Args:
        angle: Angle in degrees (0-180)
        
    Returns:
        int: PWM duty value
    """
    angle = clamp(angle, 0, 180)  # Clamp angle using utility function
    return int(SERVO_DUTY_MIN + (angle / 180) * SERVO_DUTY_RANGE)

def initialize_servo() -> bool:
    """
    Initialize the servo at the neutral position.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        move_servo_angle(NEUTRAL_POSITION)
        log_message("INFO", "Servo initialized at neutral position")
        send_message(f"{MSG_SERVO_INITIALIZED}:NEUTRAL")
        return True
    except Exception as e:
        log_message("ERROR", f"Servo initialization failed: {e}")
        return False

def move_servo(waste_type: int) -> bool:
    """
    Move the servo to the position corresponding to the waste type.
    
    Args:
        waste_type: Waste type identifier
        
    Returns:
        bool: True if successful, False otherwise
    """
    if waste_type < 0 or waste_type >= len(SERVO_POSITIONS):
        log_message("ERROR", f"Invalid waste type: {waste_type}")
        move_servo_angle(NEUTRAL_POSITION)
        return False
    
    target_angle = SERVO_POSITIONS[waste_type]
    waste_name = WASTE_TYPES[waste_type]
    active_channel = get_active_channel()
    
    log_message("INFO", f"Moving servo to {target_angle}° ({waste_name}) via {active_channel}")
    send_message(f"{MSG_SERVO_MOVING}:{PREFIX_TIPO}{waste_type}:{PREFIX_ANGULO}{target_angle}:{PREFIX_CANAL}{active_channel}")
    
    return move_servo_angle(target_angle) is not None

def move_servo_angle(angle: int) -> int:
    """
    Move servo to a specific angle.
    
    Args:
        angle: Target angle in degrees
        
    Returns:
        int: Actual angle moved to, or -1 if failed
    """
    try:
        # Clamp angle between 0 and 180 degrees using utility function
        angle = clamp(angle, 0, 180)
        
        # Move servo smoothly
        current_duty = servo.duty()
        target_duty = angle_to_duty(angle)
        
        # Smooth movement (optional)
        steps = 10
        for i in range(steps + 1):
            intermediate_duty = current_duty + (target_duty - current_duty) * i // steps
            servo.duty(intermediate_duty)
            time.sleep_ms(SERVO_MOVEMENT_DELAY // steps)
        
        # Confirm movement
        send_message(f"{MSG_SERVO_POSITIONED}:{PREFIX_ANGULO}{angle}")
        
        return angle
        
    except Exception as e:
        log_message("ERROR", f"Servo movement failed: {e}")
        send_message(f"{MSG_ERROR}:SERVO_FAILURE")
        return -1

def calibrate_servo(min_duty: int = None, max_duty: int = None) -> bool:
    """
    Calibrate servo duty cycle values.
    
    Args:
        min_duty: Minimum duty value
        max_duty: Maximum duty value
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if min_duty is not None:
            global SERVO_DUTY_MIN
            SERVO_DUTY_MIN = safe_int(min_duty, SERVO_DUTY_MIN)
        
        if max_duty is not None:
            global SERVO_DUTY_MAX
            SERVO_DUTY_MAX = safe_int(max_duty, SERVO_DUTY_MAX)
        
        global SERVO_DUTY_RANGE
        SERVO_DUTY_RANGE = SERVO_DUTY_MAX - SERVO_DUTY_MIN
        
        log_message("INFO", f"Servo calibrated: min={SERVO_DUTY_MIN}, max={SERVO_DUTY_MAX}")
        return True
        
    except Exception as e:
        log_message("ERROR", f"Servo calibration failed: {e}")
        return False

def test_servo_range() -> bool:
    """
    Test servo through its full range of motion.
    
    Returns:
        bool: True if test passed, False otherwise
    """
    try:
        log_message("INFO", "Testing servo range...")
        
        # Test minimum position
        move_servo_angle(0)
        time.sleep_ms(1000)
        
        # Test maximum position
        move_servo_angle(180)
        time.sleep_ms(1000)
        
        # Return to neutral
        move_servo_angle(NEUTRAL_POSITION)
        
        log_message("INFO", "Servo range test completed successfully")
        return True
        
    except Exception as e:
        log_message("ERROR", f"Servo range test failed: {e}")
        return False

def get_servo_status() -> dict:
    """
    Get current servo status.
    
    Returns:
        dict: Status dictionary
    """
    from utils import get_uptime_ms
    
    return {
        'pin': SERVO_PIN,
        'initialized': servo is not None,
        'neutral_position': NEUTRAL_POSITION,
        'waste_positions': SERVO_POSITIONS,
        'frequency': SERVO_FREQUENCY,
        'duty_min': SERVO_DUTY_MIN,
        'duty_max': SERVO_DUTY_MAX,
        'duty_range': SERVO_DUTY_RANGE,
        'timestamp': get_uptime_ms()
    }

# Initialize servo on import
initialize_servo()