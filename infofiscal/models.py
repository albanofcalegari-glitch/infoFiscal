"""
Modelos de datos para InfoFiscal
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Factura:
    """Representa una factura consultada en ARCA"""
    numero: str
    fecha: datetime
    cuit_emisor: str
    razon_social: str
    importe: float
    tipo_factura: str  # A, B, C, etc.
    estado: str
    cuit_receptor: Optional[str] = None
    iva: Optional[float] = None
    neto: Optional[float] = None
    total: Optional[float] = None
    observaciones: Optional[str] = None
    
    def __str__(self) -> str:
        """Representación string de la factura"""
        return (f"Factura {self.numero} - {self.fecha.strftime('%d/%m/%Y')} - "
                f"{self.razon_social} - ${self.importe:,.2f}")
    
    def to_dict(self) -> dict:
        """Convierte la factura a diccionario"""
        return {
            'numero': self.numero,
            'fecha': self.fecha.isoformat(),
            'cuit_emisor': self.cuit_emisor,
            'razon_social': self.razon_social,
            'importe': self.importe,
            'tipo_factura': self.tipo_factura,
            'estado': self.estado,
            'cuit_receptor': self.cuit_receptor,
            'iva': self.iva,
            'neto': self.neto,
            'total': self.total,
            'observaciones': self.observaciones
        }