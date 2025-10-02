# database.py - Armazenamento de classificações
import sqlite3
import json
from datetime import datetime
from utils import get_logger

logger = get_logger("Database")

class ClassificationDB:
    def __init__(self, db_path="classifications.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Inicializar banco de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    original_class TEXT NOT NULL,
                    system_class TEXT NOT NULL,
                    system_index INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    image_path TEXT,
                    processing_time REAL,
                    raw_predictions TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.success("Banco de dados inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar DB: {e}")

    def save_classification(self, result):
        """Salvar classificação no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO classifications 
                (original_class, system_class, system_index, confidence, 
                 image_path, processing_time, raw_predictions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['original_class'],
                result['system_class'],
                result['system_index'],
                result['confidence'],
                result.get('image_path'),
                result.get('processing_time'),
                json.dumps(result.get('all_predictions', []))
            ))
            conn.commit()
            conn.close()
            logger.info(f"Classificação salva: {result['system_class']} ({result['confidence']:.2%})")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar classificação: {e}")
            return False

    def get_recent_classifications(self, limit=10):
        """Obter classificações recentes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM classifications 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Erro ao buscar classificações: {e}")
            return []

    def get_statistics(self):
        """Obter estatísticas das classificações"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total de classificações
            cursor.execute('SELECT COUNT(*) FROM classifications')
            total = cursor.fetchone()[0]
            
            # Por classe
            cursor.execute('''
                SELECT system_class, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM classifications 
                GROUP BY system_class
            ''')
            by_class = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_classifications': total,
                'by_class': [
                    {'class': row[0], 'count': row[1], 'avg_confidence': row[2]}
                    for row in by_class
                ]
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}