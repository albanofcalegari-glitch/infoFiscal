#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verificar delegaciones activas en AFIP para WSFEv1
Muestra qué CUITs tienes autorizados para consultar
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from wsfev1_client import WSFEv1Client

def verificar_delegaciones():
    """Verificar qué CUITs están delegados para consulta"""
    
    mi_cuit = "20321518045"  # Tu CUIT consultor
    
    print("=" * 70)
    print(f"🔍 VERIFICANDO DELEGACIONES ACTIVAS")
    print(f"📋 CUIT Consultor: {mi_cuit}")
    print("=" * 70)
    
    # Configurar cliente
    cert_path = root_dir / 'certs' / 'certificado.crt'
    key_path = root_dir / 'certs' / 'clave_privada.key'
    
    try:
        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )
        
        print("✅ Cliente WSFEv1 creado")
        print()
        
        # Lista de CUITs para probar (puedes agregar más)
        cuits_a_probar = [
            "20321518045",  # Tu propio CUIT
            "30123456789",  # Ejemplo de CUIT empresa
            "27123456789",  # Ejemplo de CUIT persona
            "23123456789",  # Ejemplo de CUIT femenino
        ]
        
        # También agregar CUITs de tu base de datos
        try:
            import sqlite3
            conn = sqlite3.connect('infofiscal.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT cuit_dni 
                FROM clientes 
                WHERE LENGTH(cuit_dni) = 11 
                AND cuit_dni LIKE '2%' 
                OR cuit_dni LIKE '3%'
                LIMIT 10
            ''')
            
            db_cuits = [row[0] for row in cursor.fetchall()]
            cuits_a_probar.extend(db_cuits)
            conn.close()
            
            print(f"📊 Agregados {len(db_cuits)} CUITs desde la base de datos")
            
        except Exception as e:
            print(f"⚠️ No se pudo leer la base de datos: {e}")
        
        print(f"🧪 Probando {len(set(cuits_a_probar))} CUITs...")
        print()
        
        delegaciones_activas = []
        errores_autorizacion = []
        
        for cuit in set(cuits_a_probar):  # Eliminar duplicados
            try:
                print(f"🔍 Probando CUIT: {cuit}")
                
                # Intentar obtener último comprobante (Factura C, PV1)
                ultimo = client.obtener_ultimo_comprobante(cuit, 11, 1)
                
                if ultimo is not None:
                    if ultimo > 0:
                        print(f"   ✅ AUTORIZADO - Último comprobante: #{ultimo}")
                        delegaciones_activas.append({
                            'cuit': cuit,
                            'ultimo_comprobante': ultimo,
                            'status': 'autorizado'
                        })
                    else:
                        print(f"   📭 Autorizado pero sin comprobantes")
                        delegaciones_activas.append({
                            'cuit': cuit,
                            'ultimo_comprobante': 0,
                            'status': 'sin_facturas'
                        })
                else:
                    print(f"   ❌ ERROR - No autorizado o error de conexión")
                    errores_autorizacion.append(cuit)
                    
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    print(f"   ❌ NO AUTORIZADO")
                    errores_autorizacion.append(cuit)
                elif "403" in error_msg or "Forbidden" in error_msg:
                    print(f"   ❌ SIN PERMISOS")
                    errores_autorizacion.append(cuit)
                else:
                    print(f"   ⚠️ ERROR: {error_msg[:50]}...")
        
        # Mostrar resumen
        print()
        print("=" * 70)
        print("📊 RESUMEN DE DELEGACIONES")
        print("=" * 70)
        
        if delegaciones_activas:
            print(f"✅ CUITs AUTORIZADOS: {len(delegaciones_activas)}")
            print()
            
            for delegacion in delegaciones_activas:
                cuit = delegacion['cuit']
                ultimo = delegacion['ultimo_comprobante']
                status = delegacion['status']
                
                if status == 'autorizado':
                    print(f"🎯 {cuit} - ✅ CON FACTURAS (último: #{ultimo})")
                else:
                    print(f"📭 {cuit} - ⚪ Sin facturas pero autorizado")
        else:
            print("❌ NO HAY CUITs AUTORIZADOS")
            print()
            print("💡 Esto significa que:")
            print("   • No tienes delegaciones activas")
            print("   • Los CUITs probados no tienen facturación electrónica")
            print("   • Hay un problema de configuración")
        
        if errores_autorizacion:
            print(f"\n❌ CUITs SIN AUTORIZACIÓN: {len(errores_autorizacion)}")
            for cuit in errores_autorizacion[:5]:  # Mostrar máximo 5
                print(f"   • {cuit}")
            if len(errores_autorizacion) > 5:
                print(f"   ... y {len(errores_autorizacion) - 5} más")
        
        return delegaciones_activas
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        return []

def mostrar_instrucciones_delegacion():
    """Mostrar cómo delegar permisos"""
    print()
    print("=" * 70)
    print("📋 CÓMO OBTENER DELEGACIONES:")
    print("=" * 70)
    print("1. El CLIENTE debe entrar a su AFIP")
    print("2. Ir a: Administrador de Relaciones de Clave Fiscal")
    print("3. Seleccionar: Adherir Servicios")
    print("4. Buscar: 'Facturación Electrónica - Web Service'")
    print("5. Agregar tu CUIT: 20321518045")
    print("6. Tipo de relación: Representante o Consultor")
    print()
    print("📞 ALTERNATIVAMENTE:")
    print("   El cliente puede agregarte como 'Representante Fiscal'")
    print("   en Administrador de Relaciones → Representantes")
    print()
    print("⏱️ TIEMPO DE ACTIVACIÓN: 15-30 minutos")

if __name__ == "__main__":
    delegaciones = verificar_delegaciones()
    
    if not delegaciones:
        mostrar_instrucciones_delegacion()
    
    print()
    print("=" * 70)
    if delegaciones:
        print("🎉 ¡Tienes delegaciones activas!")
        print("   Puedes consultar facturas de estos CUITs")
    else:
        print("📋 Necesitas que tus clientes te deleguen permisos")
        print("   Sigue las instrucciones arriba mostradas")
    print("=" * 70)