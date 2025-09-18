# Smart-Trash-Can
Project developed for the applied research discipline at the Pontifical Catholic University of Paraná

## Overview
This project implements a **Smart Trash Bin** using an **ESP32 microcontroller**. The system automatically detects when waste is placed, classifies the type of waste using a **machine learning model**, and moves a servo to direct the waste to the correct compartment. It supports multiple communication channels (Serial, UDP/Wi-Fi) to report status and receive commands.

The system includes:

- Motion detection using a **PIR sensor**.
- Waste classification using a **TensorFlow/Keras ML model**.
- Servo-controlled sorting for six types of waste:
  - Plastic
  - Paper
  - Glass
  - Metal
  - Cardboard
  - Trash
- Communication with PC or network via **Serial** or **UDP**.
- Logging and system status reporting.
- Fallback to random classification if the ML model fails or has low confidence.

---

## Hardware Requirements

- **ESP32** development board
- **Servo motor** connected to control flap
- **PIR motion sensor**
- Optional: Wi-Fi access for UDP communication

**Pin Configuration (default)**:

| Component        | Pin      |
|-----------------|----------|
| PIR Sensor       | 34       |
| Servo Motor      | 18       |

---

## Software Requirements

- **MicroPython** on ESP32
- **TensorFlow / Keras** (for PC-side ML classification)
- Python 3.10+ (for PC scripts)
- Required Python packages:
  - `numpy`
  - `opencv-python`
  - `tensorflow`  
  *(for image processing and ML classification)*

---

## Directory Structure
```text
smart_trash_can/
│
├── ESP32/
│   ├── communication.py      # Handles Serial/UDP communication
│   ├── config.py             # System constants and hardware configuration
│   ├── main.py               # Main loop and system logic for ESP32
│   ├── sensor.py             # PIR motion sensor handling
│   ├── servo_control.py      # Servo initialization and movement functions
│   └── waste_disposal.py     # Waste processing logic
│
└── PC/
    ├── camera.py             # Image capture and preprocessing
    ├── config.py             # System constants and configuration
    ├── connections.py        # Handles Serial/UDP communication with ESP32
    ├── main.py               # Main loop and system logic for PC
    ├── ml_model.py           # ML model loading and classification
    └── utils.py              # Logging, helper functions, and fallback handling

---

## Features

### Motion Detection
- Uses a PIR sensor to detect motion.
- Sends a notification to the PC when movement is detected.

### Waste Classification
- Captures an image using a camera.
- Preprocesses the image and classifies the waste using an ML model.
- If model fails or confidence is low, falls back to a random selection.

### Servo Control
- Moves a servo to position the correct disposal compartment.
- Supports six waste types.
- Returns to neutral position after disposal.

### Communication
- **Serial** or **UDP/Wi-Fi** channels.
- Sends system messages, status updates, and error reports.
- Receives commands from PC:
  - `0-5` → select waste type
  - `SET_TYPE:X` → set waste type manually
  - `STATUS` → request current system status
  - `CANCEL` → cancel current disposal
  - `HELP` → list available commands
  - `RESET` / `RESTART` / `SHUTDOWN`

### Status Reporting
- Displays system status:
  - Active communication channel
  - Sensor motion detection
  - Servo position and initialization
  - Waste disposal process status
- Periodically reports status over active communication channel.

---

## Getting Started

1. **Install MicroPython** on ESP32.  
2. **Upload the Python scripts** to the ESP32 via USB.  
3. Configure Wi-Fi credentials in `config.py` if using UDP communication.  
4. Run `main.py` on the ESP32.  
5. Monitor system messages via Serial or UDP.

**Example commands (via Serial or UDP):**
0 # Select Plastic
SET_TYPE:3 # Set Metal manually
STATUS # Request system status
CANCEL # Cancel current disposal
HELP # Show available commands

**Workflow Example:**

1. Place trash near the bin.  
2. PIR sensor detects motion → system captures image.  
3. Image classified using ML model (or random fallback).  
4. Servo moves to correct compartment.  
5. User deposits trash → system returns servo to neutral.  
6. System reports status and waits for the next detection.

---

## Logging & Debugging
- All actions, errors, and system events are logged with emojis for easier identification:
  - ✅ Success
  - ❌ Error
  - ℹ️ Info
  - 📸 Camera capture
  - 🎯 Motion detected
  - 🤖 ML classification

---

## Customization
- **Servo positions** can be changed in `config.py` (`SERVO_POSITIONS`).
- **ML model path** can be updated in `ml_model.py` (`MODEL_PATH`).
- **Timeouts and delays** can be adjusted in `config.py`:
  - `MOVEMENT_TIMEOUT_MS`
  - `SERVO_MOVEMENT_DELAY`
  - `WASTE_PROCESSING_DELAY`
- Additional waste types can be added by updating `WASTE_TYPES` and `SERVO_POSITIONS`.

---

## License
This project is **open-source** and free to use for educational and personal projects.  
