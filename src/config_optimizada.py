"""
Configuración de optimización para infoFiscal
Este archivo centraliza las configuraciones de rendimiento
"""

import os
from pathlib import Path

# === CONFIGURACIONES DE RENDIMIENTO ===

# Cache settings
ENABLE_MODULE_CACHE = True
CACHE_TIMEOUT_MINUTES = 20
MAX_CACHE_SIZE = 100

# Database optimizations  
DB_CONNECTION_POOL = True
DB_TIMEOUT_SECONDS = 30
ENABLE_DB_CACHE = True

# AFIP service optimizations
AFIP_REQUEST_TIMEOUT = 30
AFIP_RETRY_ATTEMPTS = 3
AFIP_CACHE_AUTH_MINUTES = 20

# Flask optimizations
FLASK_THREADING = True
FLASK_PROCESSES = 1

# === CONFIGURACIONES DE AMBIENTE ===

def get_optimized_config():
    """Obtener configuración optimizada según el ambiente"""
    
    is_production = os.environ.get('INFOFISCAL_MODE') == 'production'
    
    config = {
        # Configuración base
        'DEBUG': not is_production,
        'TESTING': False,
        
        # Optimizaciones de rendimiento
        'ENABLE_CACHE': True,
        'LAZY_LOADING': True,
        'COMPRESS_RESPONSES': is_production,
        
        # Configuraciones de BD
        'DB_PATH': Path(__file__).parent / 'infofiscal.db',
        'DB_POOL_SIZE': 5 if is_production else 1,
        
        # Configuraciones AFIP
        'AFIP_TIMEOUT': AFIP_REQUEST_TIMEOUT,
        'AFIP_RETRIES': AFIP_RETRY_ATTEMPTS,
        'AFIP_CACHE_TTL': AFIP_CACHE_AUTH_MINUTES * 60,
        
        # Configuraciones de logging
        'LOG_LEVEL': 'WARNING' if is_production else 'INFO',
        'LOG_TO_FILE': is_production,
        
        # Configuraciones de seguridad
        'SECRET_KEY': os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production'),
        'SESSION_COOKIE_SECURE': is_production,
        'SESSION_COOKIE_HTTPONLY': True,
    }
    
    return config

# === FUNCIONES DE OPTIMIZACIÓN ===

def optimize_flask_app(app):
    """Aplicar optimizaciones a la aplicación Flask"""
    config = get_optimized_config()
    
    # Aplicar configuraciones
    for key, value in config.items():
        if hasattr(app.config, key) or key.isupper():
            app.config[key] = value
    
    # Optimizaciones específicas de producción
    if config.get('COMPRESS_RESPONSES'):
        try:
            from flask_compress import Compress
            Compress(app)
        except ImportError:
            pass
    
    return app

def get_db_config():
    """Obtener configuración optimizada de base de datos"""
    return {
        'check_same_thread': False,
        'timeout': DB_TIMEOUT_SECONDS,
        'isolation_level': None,  # Autocommit mode para mejor rendimiento
    }

def get_requests_config():
    """Obtener configuración optimizada para requests"""
    return {
        'timeout': AFIP_REQUEST_TIMEOUT,
        'verify': False,  # Para AFIP SSL legacy
        'stream': False,
        'allow_redirects': True,
    }

# === MONITOREO DE RENDIMIENTO ===

class PerformanceMonitor:
    """Monitor simple de rendimiento"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, operation):
        """Iniciar timer para una operación"""
        import time
        self.metrics[operation] = {'start': time.time()}
    
    def end_timer(self, operation):
        """Finalizar timer y calcular duración"""
        import time
        if operation in self.metrics:
            self.metrics[operation]['duration'] = time.time() - self.metrics[operation]['start']
            return self.metrics[operation]['duration']
        return 0
    
    def get_stats(self):
        """Obtener estadísticas de rendimiento"""
        stats = {}
        for op, data in self.metrics.items():
            if 'duration' in data:
                stats[op] = {
                    'duration_ms': round(data['duration'] * 1000, 2),
                    'duration_readable': f"{data['duration']:.3f}s"
                }
        return stats
    
    def log_slow_operations(self, threshold_seconds=1.0):
        """Log operaciones lentas"""
        for op, data in self.metrics.items():
            if 'duration' in data and data['duration'] > threshold_seconds:
                print(f"⚠️ Operación lenta detectada: {op} ({data['duration']:.3f}s)")

# Instancia global del monitor
performance_monitor = PerformanceMonitor()

# === UTILIDADES DE OPTIMIZACIÓN ===

def lazy_import(module_name):
    """Utility para lazy imports"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                module = __import__(module_name)
                return func(module, *args, **kwargs)
            except ImportError:
                print(f"Módulo {module_name} no disponible")
                return None
        return wrapper
    return decorator

def memory_efficient_json_parse(json_str, max_size=1024*1024):  # 1MB default
    """Parseo de JSON eficiente en memoria"""
    if len(json_str) > max_size:
        raise ValueError(f"JSON demasiado grande ({len(json_str)} bytes)")
    
    import json
    return json.loads(json_str)

def batch_database_operations(operations, batch_size=100):
    """Ejecutar operaciones de BD en lotes para mejor rendimiento"""
    for i in range(0, len(operations), batch_size):
        batch = operations[i:i+batch_size]
        yield batch

# === CONFIGURACIÓN DE LOGGING OPTIMIZADA ===

def setup_optimized_logging():
    """Configurar logging optimizado"""
    import logging
    
    config = get_optimized_config()
    level = getattr(logging, config['LOG_LEVEL'])
    
    # Formato optimizado
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # Configurar logger principal
    logger = logging.getLogger('infofiscal')
    logger.setLevel(level)
    logger.addHandler(console_handler)
    
    # Suprimir logs verbosos de requests en producción
    if config.get('LOG_LEVEL') == 'WARNING':
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return logger

# Configurar logging automáticamente
optimized_logger = setup_optimized_logging()