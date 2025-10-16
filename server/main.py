#!/usr/bin/env python3
"""
TrashNet Server – DRY + SOLID entry point
"""

import sys
import signal
import os
import logging
from typing import NoReturn

# --------------------------------------------------------------------------- #
# bootstrap – single responsibility: prepare Python path                       #
# --------------------------------------------------------------------------- #
SRC_DIR = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, SRC_DIR)

# --------------------------------------------------------------------------- #
# logging – single responsibility: logger factory                            #
# --------------------------------------------------------------------------- #
def build_logger(name: str = "Main") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:                      # already configured
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


LOGGER = build_logger()


# --------------------------------------------------------------------------- #
# signal handling – single responsibility: graceful shutdown                 #
# --------------------------------------------------------------------------- #
def install_signal_handlers() -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda _s, _: shutdown_gracefully())


def shutdown_gracefully() -> NoReturn:
    LOGGER.info("Recebido sinal de interrupção, encerrando...")
    sys.exit(0)


# --------------------------------------------------------------------------- #
# application life-cycle – single responsibility: start / stop               #
# --------------------------------------------------------------------------- #
def start_trashnet_server() -> int:
    """Return exit code (0 = success)."""
    from src.core.app_config import initialize_system, get_trash_net_server, get_web_dashboard

    if not initialize_system():
        LOGGER.error("Falha na inicialização do sistema")
        return 1
    
    # 🔽 Inicia o dashboard web em thread separada
    web = get_web_dashboard()
    import threading
    threading.Thread(target=web.start, daemon=True).start()

    server = get_trash_net_server()
    if not server.start():
        LOGGER.error("Falha ao iniciar servidor")
        return 1

    # keep alive until Ctrl-C or SIGTERM
    try:
        while server.running:
            signal.pause()
    except KeyboardInterrupt:
        LOGGER.info("Interrompido pelo usuário")
    finally:
        server.stop()

    return 0


# --------------------------------------------------------------------------- #
# entry-point – single responsibility: orchestrate                           #
# --------------------------------------------------------------------------- #
def main() -> int:
    install_signal_handlers()
    try:
        return start_trashnet_server()
    except Exception as exc:
        LOGGER.error(f"Erro fatal: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())