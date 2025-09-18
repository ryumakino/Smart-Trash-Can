import cv2
import numpy as np
from typing import Optional
from config import CAMERA_ID, CAPTURE_WIDTH, CAPTURE_HEIGHT, CAMERA_WARMUP_ATTEMPTS, SAVE_IMAGES, IMAGE_SAVE_PATH, IMAGE_FORMAT, IMAGE_WIDTH, IMAGE_HEIGHT, BLUR_KERNEL, DISPLAY_TIME_MS
from utils import log_error, log_success

def capture_image() -> Optional[np.ndarray]:
    """
    Capture an image from the webcam and save it locally.
    
    Returns:
        Optional[np.ndarray]: Captured image frame or None if failed
    """
    cap = cv2.VideoCapture(CAMERA_ID)
    try:
        if not cap.isOpened():
            log_error("Camera unavailable")
            return None
        
        # Settings for best quality
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        
        # Wait for the camera to adjust
        frame, ret = None, False
        for _ in range(CAMERA_WARMUP_ATTEMPTS):
            ret, frame = cap.read()
            if ret:
                continue
        
        if not ret or frame is None:
            log_error("Failed to capture image")
            return None
        
        # Save the image if enabled
        if SAVE_IMAGES:
            filename = f"{IMAGE_SAVE_PATH}.{IMAGE_FORMAT}"
            cv2.imwrite(filename, frame)
            log_success(f"Image captured and saved as {filename}")
        else:
            log_success("Image captured (not saved to disk)")
        
        return frame
        
    except Exception as e:
        log_error(f"ERROR capturing image: {e}")
        return None
    finally:
        cap.release()

def preprocess_image(frame: np.ndarray) -> Optional[np.ndarray]:
    """
    Preprocess the image for deep learning model input.
    
    Steps:
    - Resize (common for CNN models)
    - Convert BGR → RGB
    - Normalize values (0–1)
    - Apply light smoothing to reduce noise
    
    Args:
        frame: Input image frame
        
    Returns:
        Optional[np.ndarray]: Preprocessed image or None if failed
    """
    if frame is None:
        return None

    try:
        # 1. Resize to standard dimensions
        img = cv2.resize(frame, (IMAGE_WIDTH, IMAGE_HEIGHT))
        
        # 2. Convert to RGB (OpenCV uses BGR by default)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 3. Normalize to [0, 1]
        img = img.astype("float32") / 255.0
        
        # 4. Apply light smoothing to reduce noise
        img = cv2.GaussianBlur(img, BLUR_KERNEL, 0)
        
        return img
        
    except Exception as e:
        log_error(f"ERROR in image preprocessing: {e}")
        return None

def display_image(frame: np.ndarray, title: str = "Captured Image") -> None:
    """
    Display the image in a window (useful for debugging).
    
    Args:
        frame: Image to display
        title: Window title
    """
    try:
        # Convert back to BGR for display
        display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imshow(title, display_frame)
        cv2.waitKey(DISPLAY_TIME_MS)
        cv2.destroyAllWindows()
    except Exception as e:
        log_error(f"ERROR displaying image: {e}")