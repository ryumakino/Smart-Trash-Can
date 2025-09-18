import time
from machine import Timer
from config import CHANNEL_NONE, COMMUNICATION_TIMEOUT_MS
from utils import log_message

active_communication_channel = CHANNEL_NONE
last_communication_time = 0

channel_timer = Timer(0)

def detect_active_channel() -> None:
    global active_communication_channel, last_communication_time
    if time.ticks_diff(time.ticks_ms(), last_communication_time) > COMMUNICATION_TIMEOUT_MS:
        active_communication_channel = CHANNEL_NONE
        log_message("DEBUG", "Communication channel reset due to timeout")

def update_channel(channel: str) -> None:
    global active_communication_channel, last_communication_time
    active_communication_channel = channel
    last_communication_time = time.ticks_ms()

def get_active_channel() -> str:
    return active_communication_channel
