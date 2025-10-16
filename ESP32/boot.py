# boot.py - CORRIGIDO PARA IMPORTS DO CORE/
import machine
import time
import gc
import os
import sys

def log_info(msg): print(f"[BOOT] {msg}")
def log_error(msg): print(f"[BOOT-ERROR] {msg}") 
def log_warning(msg): print(f"[BOOT-WARN] {msg}")

def setup_paths():
    """Configura paths para imports do core/"""
    if '/core' not in sys.path:
        sys.path.append('/core')
    if '/lib' not in sys.path:
        sys.path.append('/lib')
    log_info("✅ Paths configurados")

def check_critical_files():
    """Verifica arquivos essenciais"""
    essential_files = ['main.py', 'core/config_manager.py']
    
    for file in essential_files:
        try:
            os.stat(file)
        except OSError:
            log_error(f"Arquivo crítico faltando: {file}")
            return False
    
    # Verificar outros arquivos do core
    core_files = ['core/utils.py', 'core/hardware_manager.py']
    for file in core_files:
        try:
            os.stat(file)
            log_info(f"✅ {file} encontrado")
        except OSError:
            log_warning(f"⚠️ {file} não encontrado")
    
    return True

def optimize_system():
    """Otimizações básicas"""
    gc.collect()
    free_mem = gc.mem_free()
    
    if free_mem < 20000:
        log_error(f"Memória muito baixa: {free_mem}")
        return False
    
    log_info(f"Memória livre: {free_mem} bytes")
    
    if hasattr(gc, 'threshold'):
        gc.threshold(50000)
    
    return True

def safe_imports():
    """Tenta imports de forma segura"""
    try:
        # Testa import do config_manager
        from core.config_manager import config_init
        log_info("✅ config_manager importado")
        return True
    except Exception as e:
        log_error(f"Erro importação: {e}")
        return False

def check_micropython_modules():
    """Verifica módulos essenciais do MicroPython"""
    essential_modules = ['uasyncio', 'machine', 'network', 'ujson']
    
    for module in essential_modules:
        try:
            __import__(module)
            log_info(f"✅ Módulo {module} disponível")
        except ImportError:
            log_error(f"❌ Módulo {module} não encontrado")
            return False
    return True

def perform_boot():
    """Executa boot tolerante a falhas"""
    log_info("=== INICIANDO TRASH AI SYSTEM ===")
    
    # 1. Configurar paths
    setup_paths()

    # 1.5 Verificar módulos MicroPython
    if not check_micropython_modules():
        log_error("Módulos essenciais faltando")
        return False
    
    # 2. Verificar memória
    if not optimize_system():
        return False
    
    # 3. Verificar arquivos críticos
    if not check_critical_files():
        return False
    
    # 4. Tentar imports
    if not safe_imports():
        log_warning("⚠️ Alguns imports falharam, continuando...")
    
    log_info("=== BOOT COMPLETO ===")
    return True

# Execução principal
try:
    if perform_boot():
        log_info("✅ Sistema pronto - iniciando main.py")
        time.sleep(1)
    else:
        log_warning("⚠️ Problemas no boot, mas tentando iniciar...")
        time.sleep(2)
        
except Exception as e:
    log_error(f"💥 Erro crítico no boot: {e}")
    time.sleep(3)
    machine.reset()