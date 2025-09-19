import time
import traceback
from setup_communication import setup_connections, comm_manager, process_esp32_messages, send_waste_type, get_connection_status
from camera import capture_image
from ml_model import setup_ml_model, classify_waste
from utils import log_info, log_error, log_success, log_warning, log_camera
from config import (
    LOG_INTERRUPTED,
    LOG_UNEXPECTED_ERROR,
    LOG_CONNECTIONS_CLOSED,
    LOG_IMAGE_FAIL,
    LOG_CLASSIFICATION_ERROR,
    LOG_SEND_OK,
    LOG_SEND_FAIL,
    WASTE_TYPES,
    LOG_MOVEMENT_DETECTED
)

# ---------------- Helper functions ----------------

def handle_movement(model):
    """
    Handle movement detection:
    - Capture image
    - Classify waste
    - Send waste type to ESP32
    """
    if not comm_manager.is_synchronized():
        log_error("Cannot process movement - communication not synchronized")
        return

    log_camera(LOG_MOVEMENT_DETECTED)

    image = capture_image()
    if image is None:
        log_error(LOG_IMAGE_FAIL)
        return

    waste_type = None
    if model:
        try:
            waste_type = classify_waste(model, image)
            if waste_type is None:
                log_error(LOG_CLASSIFICATION_ERROR)
        except Exception as e:
            log_error(f"{LOG_CLASSIFICATION_ERROR}: {e}")

    if waste_type is not None:
        if send_waste_type(waste_type):
            log_success(f"{LOG_SEND_OK}: {waste_type} ({WASTE_TYPES[waste_type]})")
        else:
            log_error(f"{LOG_SEND_FAIL}: {waste_type}")
    else:
        log_warning("Waste type not sent - classification unavailable")


def handle_message_result(message_result, model):
    """
    Process messages received from ESP32.
    """
    if message_result['needs_processing']:
        if message_result['movement_detected']:
            handle_movement(model)
        elif message_result['waste_type_selected'] != -1:
            waste_type = message_result['waste_type_selected']
            log_info(f"Waste type received from ESP32: {waste_type}")

    if message_result['error_occurred']:
        log_error(f"ESP32 reported error: {message_result['error_message']}")

    if message_result['disposal_completed']:
        log_info("Disposal process completed successfully")

# ---------------- Main ----------------

def main():
    print("=" * 50)
    print("    WASTE CLASSIFICATION SYSTEM - PC")
    print("=" * 50)

    # --- Setup communication ---
    log_info("Setting up connections to ESP32...")
    if not setup_connections():
        log_error("Failed to establish synchronized connection with ESP32")
        return

    # --- Load ML model ---
    log_info("Loading ML model...")
    model = setup_ml_model()
    if model is None:
        log_warning("Running in fallback mode without ML model")

    # --- Main loop ---
    log_info("Starting main processing loop...")
    try:
        while True:
            # Check connection periodically
            connection_status = get_connection_status()
            if not connection_status['is_synchronized']:
                log_warning("Communication lost synchronization. Attempting to reconnect...")
                if not setup_connections():
                    log_error("Failed to re-establish connection")
                    break

            # Process ESP32 messages
            message_result = process_esp32_messages()
            handle_message_result(message_result, model)

            time.sleep(0.1)

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
