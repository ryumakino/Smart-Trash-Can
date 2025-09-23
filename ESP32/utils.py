def get_logger(name):
    """Logger simples para ESP32"""
    class Logger:
        def __init__(self, name):
            self.name = name
        
        def log(self, level, message):
            print(f"[{level}] [{self.name}] {message}")
        
        def info(self, message):
            self.log("INFO", message)
        
        def error(self, message):
            self.log("ERROR", message)
        
        def warning(self, message):
            self.log("WARN", message)
    
    return Logger(name)