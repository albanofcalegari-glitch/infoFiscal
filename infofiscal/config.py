"""
Módulo de configuración para InfoFiscal
"""

import configparser
import os
from typing import Optional


class Config:
    """Maneja la configuración de la aplicación"""
    
    def __init__(self, config_file: str = "config.ini"):
        """
        Inicializa la configuración
        
        Args:
            config_file: Ruta al archivo de configuración
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser(interpolation=None)
        self._load_config()
    
    def _load_config(self):
        """Carga el archivo de configuración"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            # Crear configuración por defecto
            self._create_default_config()
    
    def _create_default_config(self):
        """Crea un archivo de configuración por defecto"""
        self.config['ARCA'] = {
            'base_url': 'https://www.arca.gob.ar',
            'timeout': '30',
            'max_retries': '3'
        }
        
        self.config['DEFAULT'] = {
            'cuit': '',
            'output_format': 'csv'
        }
        
        self.config['LOGGING'] = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
        
        # Guardar configuración por defecto
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get_arca_config(self) -> dict:
        """Obtiene la configuración de ARCA"""
        return {
            'base_url': self.config.get('ARCA', 'base_url', fallback='https://www.arca.gob.ar'),
            'timeout': self.config.getint('ARCA', 'timeout', fallback=30),
            'max_retries': self.config.getint('ARCA', 'max_retries', fallback=3)
        }
    
    def get_default_cuit(self) -> Optional[str]:
        """Obtiene el CUIT por defecto"""
        cuit = self.config.get('DEFAULT', 'cuit', fallback='')
        return cuit if cuit else None
    
    def get_output_format(self) -> str:
        """Obtiene el formato de salida por defecto"""
        return self.config.get('DEFAULT', 'output_format', fallback='csv')
    
    def get_logging_config(self) -> dict:
        """Obtiene la configuración de logging"""
        return {
            'level': self.config.get('LOGGING', 'level', fallback='INFO'),
            'format': self.config.get('LOGGING', 'format', 
                                    fallback='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        }
    
    def set_default_cuit(self, cuit: str):
        """Establece el CUIT por defecto"""
        if 'DEFAULT' not in self.config:
            self.config['DEFAULT'] = {}
        self.config['DEFAULT']['cuit'] = cuit
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)