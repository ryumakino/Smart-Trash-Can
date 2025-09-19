import time
import traceback
from config import (
    LOG_INTERRUPTED,
    LOG_UNEXPECTED_ERROR,
    LOG_CONNECTIONS_CLOSED,
    LOG_IMAGE_FAIL,
    LOG_CLASSIFICATION_ERROR,
    LOG_SEND_OK,
    LOG_SEND_FAIL
)
from comunication import setup_connections, comm_manager, process_esp32_messages, send_waste_type
from camera import process_movement, capture_image
from ml_model import setup_ml_model, classify_waste, get_random_waste_type
from utils import log_error, log_info, log_success, log_warning

def handle_movement(model):
    """Handle movement detection event"""
    log_info("Movement detected! Capturing image...")
    image_path = capture_image()
    if not image_path:
        log_error(LOG_IMAGE_FAIL)
        return
    
    # Classify waste
    if model:
        try:
            waste_type, confidence = classify_waste(model, image_path)
            log_info(f"ML Classification: Type {waste_type} with {confidence:.2f} confidence")
        except Exception as e:
            log_error(f"{LOG_CLASSIFICATION_ERROR}: {e}")
            waste_type = get_random_waste_type()
            log_info(f"Random Classification: Type {waste_type} (fallback)")
    else:
        waste_type = get_random_waste_type()
        log_info(f"Random Classification: Type {waste_type} (fallback)")
    
    # Send waste type to ESP32
    if send_waste_type(waste_type):
        log_success(f"{LOG_SEND_OK}: {waste_type}")
    else:
        log_error(f"{LOG_SEND_FAIL}: {waste_type}")

def handle_message_result(message_result, model):
    """Handle message processing results"""
    if message_result['needs_processing']:
        if message_result['movement_detected']:
            handle_movement(model)
        elif message_result['waste_type_selected'] != -1:
            waste_type = message_result['waste_type_selected']
            log_info(f"Waste type received from ESP32: {waste_type}")
            # Processar tipo de lixo recebido se necessário
    
    if message_result['error_occurred']:
        log_error(f"ESP32 reported error: {message_result['error_message']}")
        # Lógica de tratamento de erro aqui
    
    if message_result['disposal_completed']:
        log_info("Disposal process completed successfully")
        # Lógica pós-descarte aqui

def main() -> None:
    """Main function of the waste classification system."""
    print("=" * 50)
    print("    WASTE CLASSIFICATION SYSTEM - PC")
    print("=" * 50)

    # ---------------- Initialize connections ----------------
    log_info("Setting up connections to ESP32...")
    if not setup_connections():
        log_error("Failed to establish connection with ESP32")
        return

    # ---------------- Load ML model ----------------
    log_info("Loading ML model...")
    model = setup_ml_model()
    if model is None:
        log_warning("Running in fallback mode without ML model")

    # ---------------- Main loop ----------------
    log_info("Starting main processing loop...")
    try:
        while True:
            message_result = process_esp32_messages()
            handle_message_result(message_result, model)
            time.sleep(0.1)  # Pequena pausa para não sobrecarregar CPU
            
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