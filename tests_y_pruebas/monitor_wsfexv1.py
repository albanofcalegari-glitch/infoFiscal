#!/usr/bin/env python3
"""
MONITOR AUTOMÁTICO WSFEXv1
==========================
Este script verifica periódicamente si WSFEXv1 ya está funcionando
"""

import time
import sys
from datetime import datetime

sys.path.append('src')

def verificar_wsfexv1():
    """Verificar si WSFEXv1 ya funciona"""
    try:
        from wsfexv1_client import WSFEXv1Client
        
        client = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        # Probar autenticación
        tipos = client.obtener_tipos_comprobante("20321518045")
        
        if tipos and len(tipos) > 0:
            print(f"✅ {datetime.now()}: WSFEXv1 FUNCIONANDO!")
            print(f"📋 Tipos disponibles: {len(tipos)}")
            
            # Ahora buscar la factura específica
            factura = client.consultar_comprobante("20321518045", 2, 1, 235)
            if factura:
                print(f"🎉 ¡FACTURA 0002-00000235 ENCONTRADA!")
                return True
            else:
                print(f"📭 Factura específica aún no encontrada")
                
        else:
            print(f"⏳ {datetime.now()}: WSFEXv1 aún no disponible")
            
    except Exception as e:
        if "500" in str(e):
            print(f"⏳ {datetime.now()}: HTTP 500 - aún esperando...")
        else:
            print(f"❌ {datetime.now()}: Error: {str(e)[:50]}...")
    
    return False

def main():
    """Monitorear cada hora"""
    print("🔍 MONITOR WSFEXv1 INICIADO")
    print("Verificando cada hora...")
    
    while True:
        if verificar_wsfexv1():
            print("🎉 ¡ÉXITO! WSFEXv1 funcionando")
            break
        
        print("⏱️ Esperando 1 hora...")
        time.sleep(3600)  # 1 hora

if __name__ == "__main__":
    main()
