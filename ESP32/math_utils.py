def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))

def map_value(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def is_within_tolerance(value: float, target: float, tolerance: float) -> bool:
    return abs(value - target) <= tolerance

def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
