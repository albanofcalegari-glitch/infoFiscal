#!/usr/bin/env python3
"""
BÚSQUEDA ESPECÍFICA: Factura 0002-00000235 en WSFEXv1
=======================================================

La factura NO está en WSFEv1, ahora probamos en WSFEXv1
que es el servicio específico para monotributistas
"""

import sys
sys.path.append('src')

from wsfexv1_client import WSFEXv1Client

def buscar_factura_wsfexv1():
    """Buscar la factura específica en WSFEXv1"""
    print("🔍 BÚSQUEDA EN WSFEXv1")
    print("=" * 60)
    
    cuit = "27312238018" 
    punto_venta = 2
    numero = 235
    
    print(f"🎯 CUIT: {cuit}")
    print(f"📍 Factura: {punto_venta:04d}-{numero:08d}")
    print(f"🔧 Servicio: WSFEXv1 (Monotributo)")
    
    try:
        # Inicializar cliente WSFEXv1
        print(f"\n1️⃣ Inicializando cliente WSFEXv1...")
        client = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        print(f"✅ Cliente WSFEXv1 inicializado")
        
        # Tipos de comprobante específicos de WSFEXv1
        tipos_wsfexv1 = {
            1: "Factura M",           # Monotributo
            2: "Nota de Débito M", 
            3: "Nota de Crédito M",
            19: "Factura de Exportación",  # Exportación
            20: "Nota de Débito de Exportación",
            21: "Nota de Crédito de Exportación"
        }
        
        print(f"\n2️⃣ Probando en WSFEXv1...")
        
        factura_encontrada = None
        
        for tipo_id, tipo_desc in tipos_wsfexv1.items():
            print(f"\n   🔍 Probando como {tipo_desc} (tipo {tipo_id})...")
            
            try:
                # Consultar comprobante en WSFEXv1
                factura = client.consultar_comprobante(cuit, tipo_id, punto_venta, numero)
                
                if factura:
                    print(f"      🎉 ¡ENCONTRADA EN WSFEXv1!")
                    print(f"         📋 Tipo: {tipo_desc}")
                    print(f"         📄 Datos: {len(factura)} campos")
                    
                    factura_encontrada = {
                        'tipo_id': tipo_id,
                        'tipo_descripcion': tipo_desc,
                        'servicio': 'WSFEXv1',
                        'datos': factura
                    }
                    break
                else:
                    print(f"      📭 No encontrada como {tipo_desc}")
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        # Mostrar resultados
        print(f"\n3️⃣ RESULTADOS")
        print("=" * 50)
        
        if factura_encontrada:
            print("🎉 ¡FACTURA ENCONTRADA EN WSFEXv1!")
            print(f"📋 Tipo: {factura_encontrada['tipo_descripcion']}")
            print(f"🔧 Servicio: {factura_encontrada['servicio']}")
            
            datos = factura_encontrada['datos']
            print(f"\n📄 DETALLES DE LA FACTURA:")
            for campo, valor in datos.items():
                if valor and str(valor) not in ['None', 'N/A', '']:
                    print(f"   {campo}: {valor}")
            
            return factura_encontrada
        else:
            print("❌ FACTURA NO ENCONTRADA EN WSFEXv1")
            print("\n💡 POSIBLES CAUSAS:")
            print("   • Falta autorización para WSFEXv1")
            print("   • La factura está en WSMTXCA") 
            print("   • Error en los datos")
            return None
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        print(f"🔍 Detalle: {traceback.format_exc()}")
        return None

def verificar_autorizacion_wsfexv1():
    """Verificar si tenemos autorización para WSFEXv1"""
    print(f"\n4️⃣ VERIFICANDO AUTORIZACIÓN WSFEXv1")
    print("=" * 50)
    
    cuit = "27312238018"
    
    try:
        client = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        # Probar operación básica - obtener tipos de comprobante
        print("🔍 Probando autorización WSFEXv1...")
        tipos = client.obtener_tipos_comprobante(cuit)
        
        if tipos:
            print("✅ AUTORIZACIÓN WSFEXv1 CONFIRMADA")
            print(f"📋 Tipos disponibles: {len(tipos)}")
            return True
        else:
            print("❌ SIN AUTORIZACIÓN WSFEXv1 (sin tipos)")
            return False
            
    except Exception as e:
        print(f"❌ Error de autorización: {e}")
        if "500" in str(e) or "Unauthorized" in str(e) or "HTTP 500" in str(e):
            print("💡 Esto confirma que NO tienes autorización para WSFEXv1")
        return False

def main():
    """Función principal"""
    print("🎯 INVESTIGACIÓN WSFEXv1: Factura 0002-00000235")
    print("=" * 60)
    
    # Verificar autorización primero
    autorizado = verificar_autorizacion_wsfexv1()
    
    if autorizado:
        # Si tenemos autorización, buscar la factura
        factura = buscar_factura_wsfexv1()
        
        print(f"\n" + "="*60)
        print("🎯 CONCLUSIÓN")
        print("="*60)
        
        if factura:
            print(f"✅ FACTURA ENCONTRADA EN WSFEXv1")
            print(f"📋 Confirmado: Es una factura de monotributo")
            print(f"🔧 Necesitas WSFEXv1 para consultar esta factura")
        else:
            print(f"⚠️ FACTURA NO ENCONTRADA")
            print(f"🔄 Puede estar en WSMTXCA o tener otros datos")
    
    else:
        print(f"\n" + "="*60)
        print("🎯 CONCLUSIÓN PRELIMINAR")
        print("="*60)
        print("❌ SIN AUTORIZACIÓN WSFEXv1")
        print("💡 La factura 0002-00000235 probablemente esté en WSFEXv1")
        print("🔧 Necesitas solicitar autorización a AFIP para WSFEXv1")
        print("📝 Esto explica por qué no la encontramos en WSFEv1")

if __name__ == "__main__":
    main()