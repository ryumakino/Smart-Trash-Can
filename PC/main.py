import time
import traceback
from typing import Optional, Any
from config import (
    MAX_CONNECTION_ATTEMPTS,
    LOG_CONNECTION_FAIL,
    LOG_CONNECTION_ERROR,
    LOG_CONNECTION_OK,
    LOG_MODEL_OK,
    LOG_MODEL_FAIL,
    LOG_MODEL_ERROR,
    LOG_MOVEMENT_DETECTED,
    LOG_CLASSIFICATION_RANDOM,
    LOG_CLASSIFICATION_ERROR,
    LOG_SEND_OK,
    LOG_SEND_FAIL,
    LOG_IMAGE_FAIL,
    LOG_IMAGE_ERROR,
    LOG_HEADER,
    STATUS_CHECK_INTERVAL,
    MOVEMENT_CHECK_INTERVAL,
    LOG_STATUS_ERROR,
    LOG_INTERRUPTED,
    LOG_UNEXPECTED_ERROR,
    LOG_CONNECTIONS_CLOSED,
    WASTE_TYPES
)
from connections import initialize_connections, comm_manager
from camera import capture_image
from ml_model import load_model, classify_waste
from utils import send_waste_type, process_esp32_messages, get_system_status
from utils import log_error, log_info, log_success, log_camera, random_waste_fallback

def setup_connections() -> bool:
    """
    Set up connections to ESP32.
    
    Returns:
        bool: True if connections established, False otherwise
    """
    attempt = 0
    while not initialize_connections() and attempt < MAX_CONNECTION_ATTEMPTS:
        attempt += 1
        log_info(f"{LOG_CONNECTION_FAIL}. Attempt {attempt}/{MAX_CONNECTION_ATTEMPTS}")
        time.sleep(1)

    if attempt == MAX_CONNECTION_ATTEMPTS:
        log_error(LOG_CONNECTION_ERROR)
        return False
    else:
        log_success(LOG_CONNECTION_OK)
        return True

def setup_ml_model() -> Optional[Any]:
    """
    Set up the machine learning model.
    
    Returns:
        Optional[Any]: Loaded model or None if failed
    """
    try:
        model = load_model()
        if model:
            log_success(LOG_MODEL_OK)
            return model
        else:
            log_info(LOG_MODEL_FAIL)
            return None
    except Exception as e:
        log_error(f"{LOG_MODEL_ERROR}: {e}")
        traceback.print_exc()
        log_info(LOG_MODEL_FAIL)
        return None

def process_movement(model: Optional[Any]) -> None:
    """
    Process movement detection and waste classification.
    
    Args:
        model: Loaded ML model or None
    """
    log_camera(LOG_MOVEMENT_DETECTED)
    try:
        image = capture_image()
        if image is not None:
            try:
                waste_type = classify_waste(model, image) if model else None
                if waste_type is None:
                    waste_type = random_waste_fallback(LOG_CLASSIFICATION_RANDOM)
            except Exception as e:
                log_error(f"{LOG_CLASSIFICATION_ERROR}: {e}")
                traceback.print_exc()
                waste_type = random_waste_fallback(LOG_CLASSIFICATION_RANDOM)

            # Send waste type to ESP32
            if send_waste_type(waste_type):
                log_success(f"{LOG_SEND_OK}: {waste_type} ({WASTE_TYPES[waste_type]})")
            else:
                log_error(LOG_SEND_FAIL)
        else:
            log_error(LOG_IMAGE_FAIL)
    except Exception as e:
        log_error(f"{LOG_IMAGE_ERROR}: {e}")
        traceback.print_exc()

# -------------------------
# Main Function
# -------------------------

def main() -> None:
    """Main function of the waste classification system."""
    print("=" * 50)
    print(f"    {LOG_HEADER}")
    print("=" * 50)

    # ---------------- Initialize connections ----------------
    if not setup_connections():
        return

    # ---------------- Load ML model ----------------
    model = setup_ml_model()

    # ---------------- Main loop ----------------
    last_status_check = 0
    
    try:
        while True:
            # Process ESP32 messages
            movement_detected = process_esp32_messages()

            # If movement detected, capture and process image
            if movement_detected:
                process_movement(model)

            # Periodic system status check
            current_time = time.time()
            if current_time - last_status_check > STATUS_CHECK_INTERVAL:
                try:
                    get_system_status()
                    last_status_check = current_time
                except Exception as e:
                    log_error(f"{LOG_STATUS_ERROR}: {e}")
                    traceback.print_exc()

            time.sleep(MOVEMENT_CHECK_INTERVAL)

    except KeyboardInterrupt:
        log_info(LOG_INTERRUPTED)
    except Exception as e:
        log_error(f"{LOG_UNEXPECTED_ERROR}: {e}")
        traceback.print_exc()
    finally:
        comm_manager.close_connections()
        log_success(LOG_CONNECTIONS_CLOSED)

if __name__ == "__main__":
    main()