from src.web.dashboard import create_app
from src.core.service_factory import ServiceFactory
from src.core.base_classes import BaseService
import threading

class WebDashboard(BaseService):
    def __init__(self):
        super().__init__()
        self.flask_app = create_app()

    def initialize(self):
        self._initialized = True
        self.logger.info("WebDashboard inicializado")
        return True

    def start(self):
        self.flask_app.run(
            host="0.0.0.0",
            port=5000,
            threaded=True,
            debug=False
        )

# Registra o serviço no sistema
ServiceFactory.register_service("web_dashboard", WebDashboard)