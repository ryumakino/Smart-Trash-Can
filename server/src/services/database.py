# database.py - Banco de dados para classificações (Refatorado)
import sqlite3
import os
from datetime import datetime
from src.core.base_classes import BaseService, ConfigurableMixin

class ClassificationDB(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('system')
        self.db_path = None
        self.init_db()

    def initialize(self):
        """Inicializar banco de dados"""
        if self._initialized:
            return True
            
        try:
            data_dir = self.get_config_value('DATA_DIR', 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            self.db_path = os.path.join(data_dir, "classifications.db")
            self._initialized = True
            self.logger.success("✅ ClassificationDB inicializado")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização: {e}")
            return False

    def init_db(self):
        """Inicializar estrutura do banco de dados"""
        if not self.initialize():
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS classifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        original_class TEXT NOT NULL,
                        system_class TEXT NOT NULL,
                        system_index INTEGER NOT NULL,
                        confidence REAL NOT NULL,
                        image_path TEXT,
                        processing_time REAL,
                        model_type TEXT,
                        is_mock BOOLEAN DEFAULT FALSE,
                        device_id TEXT
                    )
                ''')
                conn.commit()
            self.logger.success("✅ Banco de dados inicializado")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
            return False

    def save_classification(self, result):
        """Salvar classificação no banco de dados"""
        if not self._initialized:
            self.logger.error("Banco de dados não inicializado")
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO classifications 
                    (timestamp, original_class, system_class, system_index, confidence, 
                     image_path, processing_time, model_type, is_mock, device_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.get('timestamp', datetime.now().isoformat()),
                    result.get('original_class', ''),
                    result.get('system_class', ''),
                    result.get('system_index', -1),
                    result.get('confidence', 0.0),
                    result.get('image_path', ''),
                    result.get('processing_time', 0.0),
                    result.get('model_type', 'unknown'),
                    result.get('is_mock', False),
                    result.get('device_id', '')
                ))
                conn.commit()
            self.logger.debug("Classificação salva no banco de dados")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar classificação: {e}")
            return False

    def get_recent_classifications(self, limit=50):
        """Obter classificações recentes"""
        if not self._initialized:
            self.logger.error("Banco de dados não inicializado")
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM classifications 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                results = cursor.fetchall()
                self.logger.debug(f"Recuperadas {len(results)} classificações recentes")
                return results
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter classificações: {e}")
            return []

    def get_statistics(self):
        """Obter estatísticas do banco de dados"""
        if not self._initialized:
            self.logger.error("Banco de dados não inicializado")
            return {}
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total de classificações
                cursor.execute('SELECT COUNT(*) FROM classifications')
                total = cursor.fetchone()[0]
                
                # Classificações por tipo
                cursor.execute('''
                    SELECT system_class, COUNT(*) 
                    FROM classifications 
                    GROUP BY system_class
                ''')
                by_class = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Média de confiança
                cursor.execute('SELECT AVG(confidence) FROM classifications')
                avg_confidence = cursor.fetchone()[0] or 0
                
                # Última classificação
                cursor.execute('''
                    SELECT timestamp, system_class, confidence 
                    FROM classifications 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''')
                last_classification = cursor.fetchone()
                
                stats = {
                    'total_classifications': total,
                    'classifications_by_type': by_class,
                    'average_confidence': round(avg_confidence, 3),
                    'last_classification': {
                        'timestamp': last_classification[0] if last_classification else None,
                        'class': last_classification[1] if last_classification else None,
                        'confidence': last_classification[2] if last_classification else None
                    }
                }
                
                self.logger.debug("Estatísticas do banco recuperadas")
                return stats
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {}

    def get_status(self):
        """Obter status do banco de dados"""
        base_status = super().get_status()
        base_status.update({
            'db_path': self.db_path,
            'db_initialized': self._initialized,
            'total_records': self.get_statistics().get('total_classifications', 0)
        })
        return base_status