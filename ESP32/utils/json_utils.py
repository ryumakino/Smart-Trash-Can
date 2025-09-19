import ujson
from .hardware_utils import log_message

def json_encode(obj):
    """Simple JSON encoder for MicroPython"""
    if isinstance(obj, dict):
        items = []
        for k, v in obj.items():
            items.append(f'"{k}":{json_encode(v)}')
        return "{" + ",".join(items) + "}"
    elif isinstance(obj, list):
        items = [json_encode(item) for item in obj]
        return "[" + ",".join(items) + "]"
    elif isinstance(obj, str):
        return f'"{obj}"'
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif obj is None:
        return "null"
    else:
        return str(obj)

def json_decode(json_str: str) -> dict:
    try:
        return ujson.loads(json_str)
    except Exception as e:
        log_message("ERROR", f"JSON decode failed: {e}")
        return {}
