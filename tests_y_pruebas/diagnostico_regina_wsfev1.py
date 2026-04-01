"""
Diagnóstico específico para WSFEv1 con Regina Cereto
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

from wsfev1_client import WSFEv1Client

def diagnostico_regina():
    """Diagnóstico específico para Regina Cereto"""
    
    print("🔍 DIAGNÓSTICO WSFEv1 - REGINA CERETO")
    print("=" * 50)
    
    cuit_regina = "27312238018"
    
    try:
        # Configurar rutas de certificados
        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'
        
        print(f"📄 Certificado: {cert_path}")
        print(f"🔑 Clave: {key_path}")
        print(f"👤 CUIT Regina: {cuit_regina}")
        
        # Verificar archivos
        if not cert_path.exists():
            print(f"❌ Certificado no encontrado: {cert_path}")
            return
        if not key_path.exists():
            print(f"❌ Clave no encontrada: {key_path}")
            return
            
        print("✅ Archivos de certificado encontrados")
        
        # Crear cliente WSFEv1
        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )
        
        print("\n🔐 Probando autenticación WSAA...")
        try:
            token, sign = client.autenticar_wsaa(cuit_regina)
            if token and sign:
                print("✅ Autenticación WSAA exitosa")
                print(f"   Token: {token[:20]}...")
                print(f"   Sign: {sign[:20]}...")
            else:
                print("❌ Autenticación WSAA falló - Token/Sign vacíos")
                return
        except Exception as e:
            print(f"❌ Error en autenticación WSAA: {e}")
            return
            
        print("\n📋 Probando obtener último comprobante (Factura B, PV1)...")
        try:
            ultimo = client.obtener_ultimo_comprobante(cuit_regina, 6, 1)
            print(f"✅ Último comprobante: {ultimo}")
        except Exception as e:
            print(f"❌ Error obteniendo último comprobante: {e}")
            print(f"   Tipo de error: {type(e)}")
            if hasattr(e, 'response'):
                print(f"   HTTP Status: {e.response.status_code}")
                print(f"   Response: {e.response.text[:500]}...")
            import traceback
            traceback.print_exc()
            
        print("\n📋 Probando buscar comprobantes en rango...")
        try:
            facturas = client.buscar_comprobantes_rango(
                cuit=cuit_regina,
                tipos_comprobante=[6],  # Solo Factura B
                puntos_venta=[1],       # Solo PV 1
                limite_por_tipo=5
            )
            print(f"✅ Facturas encontradas: {len(facturas)}")
            for factura in facturas[:2]:  # Solo mostrar las primeras 2
                print(f"   - {factura}")
        except Exception as e:
            print(f"❌ Error buscando comprobantes: {e}")
            print(f"   Tipo de error: {type(e)}")
            if hasattr(e, 'response'):
                print(f"   HTTP Status: {e.response.status_code}")
                print(f"   Response: {e.response.text[:500]}...")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostico_regina()