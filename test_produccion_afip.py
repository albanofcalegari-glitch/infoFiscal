#!/usr/bin/env python3
"""
Test de producción AFIP - CUIT 20321518045
Prueba autenticación WSAA y consulta de facturas electrónicas en producción
"""

import sys
from pathlib import Path
import os

# Configurar ambiente de producción
os.environ['INFOFISCAL_MODE'] = 'production'

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_produccion_afip():
    """Test completo de servicios AFIP en producción"""
    
    print("🚀 PROBANDO SERVICIOS AFIP EN PRODUCCIÓN")
    print("=" * 50)
    print(f"CUIT: 20321518045")
    print(f"Ambiente: PRODUCCIÓN")
    print()
    
    try:
        from arca_service_simple import ARCAServiceSimple, verificar_conexion_afip
        
        # Paso 1: Verificar conectividad básica
        print("🔗 PASO 1: Verificando conectividad...")
        conectividad, mensaje = verificar_conexion_afip()
        if conectividad:
            print(f"✅ Conectividad OK: {mensaje}")
        else:
            print(f"❌ Error conectividad: {mensaje}")
            return False
        
        # Paso 2: Crear instancia del servicio
        print("\n🔧 PASO 2: Creando servicio AFIP...")
        cuit = "20321518045"
        cert_path = "certs/certificado.crt"
        key_path = "certs/clave_privada.key"
        
        # Verificar certificados
        if not Path(cert_path).exists():
            print(f"❌ Certificado no encontrado: {cert_path}")
            return False
        if not Path(key_path).exists():
            print(f"❌ Clave privada no encontrada: {key_path}")
            return False
        
        print("✅ Certificados encontrados")
        
        # Crear servicio (testing=False para producción)
        service = ARCAServiceSimple(
            cuit=cuit,
            cert_path=cert_path,
            key_path=key_path,
            testing=False  # PRODUCCIÓN
        )
        print("✅ Servicio AFIP creado para PRODUCCIÓN")
        
        # Paso 3: Autenticación WSAA
        print("\n🔐 PASO 3: Autenticando con WSAA...")
        auth_data = service.autenticar()
        
        if auth_data and 'token' in auth_data:
            print("✅ AUTENTICACIÓN WSAA EXITOSA!")
            print(f"   Token: {auth_data['token'][:50]}...")
            print(f"   Sign: {auth_data['sign'][:50]}...")
        else:
            print("❌ FALLO EN AUTENTICACIÓN WSAA")
            print("   Posibles causas:")
            print("   - Servicios no habilitados en AFIP")
            print("   - Certificado no asociado al CUIT")
            print("   - OpenSSL no disponible")
            return False
        
        # Paso 4: Consulta WSFE - Último autorizado
        print("\n📄 PASO 4: Consultando último comprobante autorizado...")
        
        # Probar varios puntos de venta y tipos comunes
        puntos_venta = [1, 2, 3]  # PV más comunes
        tipos_cbte = [1, 6, 11, 13]  # Facturas más comunes
        
        resultados_consulta = {}
        
        for pv in puntos_venta:
            resultados_consulta[pv] = {}
            for tipo in tipos_cbte:
                try:
                    ultimo = service.wsfe_fecomp_ultimo_autorizado(pv, tipo)
                    resultados_consulta[pv][tipo] = ultimo
                    
                    if ultimo is not None and ultimo > 0:
                        print(f"   ✅ PV {pv}, Tipo {tipo}: Último = {ultimo}")
                    elif ultimo == 0:
                        print(f"   ⚪ PV {pv}, Tipo {tipo}: Sin comprobantes")
                    else:
                        print(f"   ❌ PV {pv}, Tipo {tipo}: Error en consulta")
                        
                except Exception as e:
                    print(f"   ⚠️ PV {pv}, Tipo {tipo}: Excepción - {str(e)[:50]}")
        
        # Paso 5: Análisis de resultados
        print(f"\n📊 PASO 5: Análisis de resultados...")
        
        total_consultas = 0
        consultas_exitosas = 0
        comprobantes_encontrados = 0
        
        for pv, tipos in resultados_consulta.items():
            for tipo, resultado in tipos.items():
                total_consultas += 1
                if resultado is not None:
                    consultas_exitosas += 1
                    if resultado > 0:
                        comprobantes_encontrados += 1
        
        print(f"   📈 Consultas totales: {total_consultas}")
        print(f"   ✅ Consultas exitosas: {consultas_exitosas}")
        print(f"   📄 Con comprobantes: {comprobantes_encontrados}")
        
        # Paso 6: Test de enumeración completa
        if comprobantes_encontrados > 0:
            print(f"\n🔍 PASO 6: Test de enumeración completa...")
            
            try:
                base_dir = Path(__file__).parent / 'test_produccion'
                resultado_enum = service.enumerar_y_guardar(
                    cuit_objetivo=cuit,
                    base_dir=base_dir,
                    max_por_tipo=2  # Solo 2 por tipo para test
                )
                
                print(f"   Status: {resultado_enum.get('status', 'desconocido')}")
                print(f"   Mensaje: {resultado_enum.get('mensaje', 'Sin mensaje')}")
                
                if resultado_enum.get('status') == 'ok':
                    guardados = resultado_enum.get('total_guardados', 0)
                    print(f"   ✅ Comprobantes guardados: {guardados}")
                else:
                    print(f"   ⚠️ No se pudieron enumerar comprobantes")
                    
            except Exception as e:
                print(f"   ❌ Error en enumeración: {str(e)}")
        
        # Resumen final
        print(f"\n🎯 RESUMEN FINAL:")
        if consultas_exitosas > 0:
            print("✅ CONEXIÓN A PRODUCCIÓN EXITOSA")
            print("✅ Autenticación WSAA funcionando")
            print("✅ Consultas WSFE respondiendo")
            
            if comprobantes_encontrados > 0:
                print("✅ Comprobantes electrónicos disponibles")
                print("🎉 ¡AFIP PRODUCCIÓN COMPLETAMENTE FUNCIONAL!")
            else:
                print("⚪ Sin comprobantes en los PV consultados")
                print("💡 Puede necesitar emitir comprobantes primero")
                
            return True
        else:
            print("❌ PROBLEMAS EN PRODUCCIÓN")
            print("💡 Verificar configuración AFIP")
            return False
            
    except ImportError as e:
        print(f"❌ Error importando módulos: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

def mostrar_urls_produccion():
    """Mostrar URLs que se están usando en producción"""
    print(f"\n🔗 URLs DE PRODUCCIÓN:")
    print("=" * 30)
    print("WSAA: https://wsaa.afip.gov.ar/ws/services/LoginCms")
    print("WSFE: https://servicios1.afip.gov.ar/wsfev1/service.asmx")
    print()
    print("💡 Estas son las URLs reales de AFIP (no testing)")

if __name__ == "__main__":
    print("🏭 CONFIGURANDO PRUEBA DE PRODUCCIÓN AFIP")
    print("=" * 50)
    
    mostrar_urls_produccion()
    
    print("⚠️  IMPORTANTE:")
    print("   - Usando servicios REALES de AFIP")
    print("   - CUIT debe tener servicios habilitados") 
    print("   - Certificado debe estar asociado")
    print("   - OpenSSL debe estar disponible")
    print()
    
    input("Presiona ENTER para continuar con la prueba...")
    
    exito = test_produccion_afip()
    
    if exito:
        print(f"\n🎉 ¡PRUEBA DE PRODUCCIÓN EXITOSA!")
        print("Tu aplicación puede usar servicios AFIP reales")
    else:
        print(f"\n⚠️ PRUEBA DE PRODUCCIÓN CON PROBLEMAS")
        print("Revisar configuración AFIP antes de usar en producción")