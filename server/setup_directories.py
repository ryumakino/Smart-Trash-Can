# setup_directories.py - Configurar estrutura de diretórios
import os
from config import SystemConfig

def setup_directories():
    """Criar estrutura de diretórios necessária"""
    directories = [
        SystemConfig.DATA_DIR,
        SystemConfig.MODELS_DIR, 
        SystemConfig.LOGS_DIR,
        SystemConfig.TEST_IMAGES_DIR,
        "templates"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Diretório criado: {directory}")
    
    # Criar arquivo modelo vazio se não existir
    model_path = "models/trashnet_model.h5"
    if not os.path.exists(model_path):
        open(model_path, 'w').close()
        print(f"📁 Arquivo modelo criado: {model_path}")
    
    print("🎯 Estrutura de diretórios configurada com sucesso!")

if __name__ == "__main__":
    setup_directories()