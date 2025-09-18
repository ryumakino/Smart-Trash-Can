import time
import traceback
from config import *
from connections import initialize_connections, comm_manager
from camera import capture_image
from ml_model import load_model, classify_waste
from utils import send_waste_type, process_esp32_messages, get_system_status
from utils import log_message, log_error, log_info, log_success, log_camera, random_waste_fallback

# -------------------------
# Main Function
# -------------------------
def main():
    print("=" * 50)
    print(f"    {LOG_HEADER}")
    print("=" * 50)

    # ---------------- Initialize connections ----------------
    attempt = 0
    while not initialize_connections() and attempt < MAX_CONNECTION_ATTEMPTS:
        attempt += 1
        log_info(f"{LOG_CONNECTION_FAIL}. Attempt {attempt}/{MAX_CONNECTION_ATTEMPTS}")
        time.sleep(1)

    if attempt == MAX_CONNECTION_ATTEMPTS:
        log_error(LOG_CONNECTION_ERROR)
        return
    else:
        log_success(LOG_CONNECTION_OK)

    # ---------------- Load ML model ----------------
    try:
        model = load_model()
        if model:
            log_success(LOG_MODEL_OK)
        else:
            log_info(LOG_MODEL_FAIL)
    except Exception as e:
        log_error(f"{LOG_MODEL_ERROR}: {e}")
        traceback.print_exc()
        log_info(LOG_MODEL_FAIL)
        model = None

    # ---------------- Main loop ----------------
    last_status_check = 0
    
    try:
        while True:
            # Process ESP32 messages
            movement_detected = process_esp32_messages()

            # If movement detected, capture and process image
            if movement_detected:
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