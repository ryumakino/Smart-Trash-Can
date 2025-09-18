import ujson
from .hardware_utils import log_message

def json_encode(data: dict) -> str:
    try:
        return ujson.dumps(data)
    except Exception as e:
        log_message("ERROR", f"JSON encode failed: {e}")
        return "{}"

def json_decode(json_str: str) -> dict:
    try:
        return ujson.loads(json_str)
    except Exception as e:
        log_message("ERROR", f"JSON decode failed: {e}")
        return {}
