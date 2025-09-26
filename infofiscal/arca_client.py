"""
Cliente para consultar facturas en ARCA (Administración de Rentas de la Ciudad Autónoma)
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import pandas as pd
from .config import Config
from .models import Factura


class ARCAClient:
    """Cliente para interactuar con el sistema ARCA"""
    
    def __init__(self, config: Config, verbose: bool = False):
        """
        Inicializa el cliente ARCA
        
        Args:
            config: Configuración de la aplicación
            verbose: Mostrar información detallada
        """
        self.config = config
        self.verbose = verbose
        self.arca_config = config.get_arca_config()
        self.session = requests.Session()
        
        # Configurar logging
        log_config = config.get_logging_config()
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format']
        )
        self.logger = logging.getLogger(__name__)
        
        # Headers para simular un navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def _validar_cuit(self, cuit: str) -> bool:
        """
        Valida el formato del CUIT
        
        Args:
            cuit: CUIT a validar
            
        Returns:
            True si el CUIT es válido
        """
        # Remover guiones y espacios
        cuit_limpio = cuit.replace('-', '').replace(' ', '')
        
        # Verificar que tenga 11 dígitos
        if len(cuit_limpio) != 11 or not cuit_limpio.isdigit():
            return False
        
        # Verificar dígito verificador (algoritmo CUIT)
        multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(cuit_limpio[i]) * multiplicadores[i] for i in range(10))
        resto = suma % 11
        
        if resto < 2:
            digito_verificador = resto
        else:
            digito_verificador = 11 - resto
        
        return int(cuit_limpio[10]) == digito_verificador
    
    def _formatear_fecha(self, fecha_str: str) -> datetime:
        """
        Convierte string de fecha DD/MM/YYYY a datetime
        
        Args:
            fecha_str: Fecha en formato DD/MM/YYYY
            
        Returns:
            Objeto datetime
        """
        try:
            return datetime.strptime(fecha_str, '%d/%m/%Y')
        except ValueError:
            raise ValueError(f"Formato de fecha inválido: {fecha_str}. Use DD/MM/YYYY")
    
    def consultar_facturas(self, cuit: str, fecha_desde: Optional[str] = None, 
                          fecha_hasta: Optional[str] = None) -> List[Factura]:
        """
        Consulta facturas en ARCA para un CUIT específico
        
        Args:
            cuit: CUIT del contribuyente
            fecha_desde: Fecha desde (DD/MM/YYYY)
            fecha_hasta: Fecha hasta (DD/MM/YYYY)
            
        Returns:
            Lista de facturas encontradas
        """
        if not self._validar_cuit(cuit):
            raise ValueError(f"CUIT inválido: {cuit}")
        
        # Si no se especifican fechas, usar el último mes
        if not fecha_desde or not fecha_hasta:
            fecha_hasta_dt = datetime.now()
            fecha_desde_dt = fecha_hasta_dt - timedelta(days=30)
        else:
            fecha_desde_dt = self._formatear_fecha(fecha_desde)
            fecha_hasta_dt = self._formatear_fecha(fecha_hasta)
        
        if self.verbose:
            print(f"Consultando facturas para CUIT {cuit}")
            print(f"Periodo: {fecha_desde_dt.strftime('%d/%m/%Y')} - {fecha_hasta_dt.strftime('%d/%m/%Y')}")
        
        # Simular consulta (en una implementación real, aquí iría la lógica de scraping o API)
        facturas = self._simular_consulta_facturas(cuit, fecha_desde_dt, fecha_hasta_dt)
        
        self.logger.info(f"Se encontraron {len(facturas)} facturas para CUIT {cuit}")
        return facturas
    
    def _simular_consulta_facturas(self, cuit: str, fecha_desde: datetime, 
                                  fecha_hasta: datetime) -> List[Factura]:
        """
        Simula la consulta de facturas (placeholder para implementación real)
        
        Args:
            cuit: CUIT del contribuyente
            fecha_desde: Fecha desde
            fecha_hasta: Fecha hasta
            
        Returns:
            Lista de facturas simuladas
        """
        # En una implementación real, aquí se haría el scraping del sitio ARCA
        # Por ahora, generamos datos de ejemplo
        
        facturas = []
        
        # Generar algunas facturas de ejemplo
        for i in range(1, 4):
            fecha = fecha_desde + timedelta(days=i * 5)
            if fecha <= fecha_hasta:
                factura = Factura(
                    numero=f"0001-{i:08d}",
                    fecha=fecha,
                    cuit_emisor=cuit,
                    razon_social="Empresa de Ejemplo S.A.",
                    importe=1000.00 + (i * 500),
                    tipo_factura="A",
                    estado="Activa"
                )
                facturas.append(factura)
        
        if self.verbose:
            print(f"Simulación: generadas {len(facturas)} facturas de ejemplo")
        
        return facturas
    
    def exportar_facturas(self, facturas: List[Factura], archivo_salida: str):
        """
        Exporta las facturas a un archivo CSV o Excel
        
        Args:
            facturas: Lista de facturas
            archivo_salida: Ruta del archivo de salida
        """
        if not facturas:
            raise ValueError("No hay facturas para exportar")
        
        # Convertir facturas a DataFrame
        datos = []
        for factura in facturas:
            datos.append({
                'Número': factura.numero,
                'Fecha': factura.fecha.strftime('%d/%m/%Y'),
                'CUIT Emisor': factura.cuit_emisor,
                'Razón Social': factura.razon_social,
                'Importe': factura.importe,
                'Tipo': factura.tipo_factura,
                'Estado': factura.estado
            })
        
        df = pd.DataFrame(datos)
        
        # Exportar según la extensión del archivo
        if archivo_salida.lower().endswith('.xlsx'):
            df.to_excel(archivo_salida, index=False)
        elif archivo_salida.lower().endswith('.csv'):
            df.to_csv(archivo_salida, index=False, encoding='utf-8')
        else:
            # Por defecto, exportar como CSV
            df.to_csv(archivo_salida + '.csv', index=False, encoding='utf-8')
        
        self.logger.info(f"Facturas exportadas a: {archivo_salida}")
    
    def __del__(self):
        """Cierra la sesión al destruir el objeto"""
        if hasattr(self, 'session'):
            self.session.close()