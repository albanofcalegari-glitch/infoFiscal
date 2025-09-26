#!/usr/bin/env python3
"""
Script de prueba para InfoFiscal
"""

import os
import sys
from datetime import datetime

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infofiscal.config import Config
from infofiscal.arca_client import ARCAClient


def test_config():
    """Prueba la configuración"""
    print("🔧 Probando configuración...")
    config = Config()
    
    # Verificar configuración de ARCA
    arca_config = config.get_arca_config()
    assert arca_config['base_url'] == 'https://www.arca.gob.ar'
    assert arca_config['timeout'] == 30
    print("✅ Configuración OK")


def test_cuit_validation():
    """Prueba la validación de CUIT"""
    print("🔍 Probando validación de CUIT...")
    config = Config()
    client = ARCAClient(config)
    
    # CUIT válido
    assert client._validar_cuit('20123456786') == True
    
    # CUIT inválido
    assert client._validar_cuit('20123456789') == False
    assert client._validar_cuit('123456789') == False
    assert client._validar_cuit('abc1234567890') == False
    
    print("✅ Validación de CUIT OK")


def test_consulta_facturas():
    """Prueba la consulta de facturas"""
    print("📋 Probando consulta de facturas...")
    config = Config()
    client = ARCAClient(config)
    
    # Consultar facturas con CUIT válido
    facturas = client.consultar_facturas('20123456786')
    
    assert len(facturas) > 0
    assert all(factura.numero for factura in facturas)
    assert all(factura.cuit_emisor == '20123456786' for factura in facturas)
    
    print(f"✅ Consulta OK - Se encontraron {len(facturas)} facturas")


def test_export():
    """Prueba la exportación de facturas"""
    print("💾 Probando exportación...")
    config = Config()
    client = ARCAClient(config)
    
    # Obtener facturas
    facturas = client.consultar_facturas('20123456786')
    
    # Exportar a CSV
    csv_file = '/tmp/test_facturas.csv'
    client.exportar_facturas(facturas, csv_file)
    assert os.path.exists(csv_file)
    
    # Exportar a Excel
    excel_file = '/tmp/test_facturas.xlsx'
    client.exportar_facturas(facturas, excel_file)
    assert os.path.exists(excel_file)
    
    print("✅ Exportación OK")
    
    # Limpiar archivos de prueba
    os.remove(csv_file)
    os.remove(excel_file)


def main():
    """Ejecuta todas las pruebas"""
    print("🚀 Ejecutando pruebas de InfoFiscal...\n")
    
    try:
        test_config()
        test_cuit_validation()
        test_consulta_facturas()
        test_export()
        
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()