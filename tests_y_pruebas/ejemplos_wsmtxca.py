#!/usr/bin/env python3
"""
Ejemplos de uso del cliente WSMTXCA
Casos de uso reales para consulta de facturas electrónicas con códigos MTX
"""

from wsmtxca_client import WSMTXCAClient, crear_cliente_wsmtxca, consulta_rapida_wsmtxca
from datetime import datetime

def ejemplo_consulta_basica():
    """Ejemplo básico: consultar una factura específica"""
    print("📋 === EJEMPLO 1: CONSULTA BÁSICA ===")
    
    try:
        # Usar tu CUIT real
        cuit = "20321518045"  # Tu CUIT
        
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        # Consultar factura específica
        resultado = client.consultar_comprobante(
            cuit_representada=cuit,
            tipo_comprobante=1,    # Factura A
            punto_venta=1,
            numero_comprobante=1
        )
        
        if resultado:
            print("✅ Comprobante encontrado:")
            print(f"   Tipo: {resultado.get('tipo_comprobante')}")
            print(f"   Fecha: {resultado.get('fecha_emision')}")
            print(f"   Receptor: {resultado.get('receptor_denominacion')}")
            print(f"   Total: ${resultado.get('importe_total')}")
            print(f"   CAE: {resultado.get('cae')}")
            print(f"   Items: {resultado.get('cantidad_items')}")
            
            # Mostrar algunos items
            items = resultado.get('items', [])
            if items:
                print("\n🛍️ Primeros items:")
                for i, item in enumerate(items[:3], 1):
                    print(f"   {i}. {item.get('descripcion')} - Código MTX: {item.get('codigo_mtx')}")
            
            return resultado
        else:
            print("📭 Comprobante no encontrado")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def ejemplo_consulta_monotributo():
    """Ejemplo: consultar facturas de monotributo (tipo 51)"""
    print("\n📋 === EJEMPLO 2: FACTURAS MONOTRIBUTO ===")
    
    try:
        cuit = "20321518045"  # Tu CUIT
        
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        # Probar varios números de factura M
        for numero in range(1, 6):
            print(f"\n🔍 Consultando Factura M #{numero}...")
            
            resultado = client.consultar_comprobante(
                cuit_representada=cuit,
                tipo_comprobante=51,  # Factura M
                punto_venta=2,        # Punto venta monotributo
                numero_comprobante=numero
            )
            
            if resultado:
                print(f"   ✅ Encontrada - Total: ${resultado.get('importe_total')}")
            else:
                print(f"   📭 No encontrada")
                
    except Exception as e:
        print(f"❌ Error: {e}")

def ejemplo_consulta_multiple():
    """Ejemplo: consultar múltiples comprobantes en lote"""
    print("\n📋 === EJEMPLO 3: CONSULTA MÚLTIPLE ===")
    
    try:
        cuit = "20321518045"  # Tu CUIT
        
        # Lista de comprobantes a consultar
        comprobantes = [
            {'tipo': 1, 'punto_venta': 1, 'numero': 1},
            {'tipo': 1, 'punto_venta': 1, 'numero': 2}, 
            {'tipo': 6, 'punto_venta': 1, 'numero': 1},
            {'tipo': 51, 'punto_venta': 2, 'numero': 1},
            {'tipo': 51, 'punto_venta': 2, 'numero': 2}
        ]
        
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        resultados = client.consultar_multiples_comprobantes(cuit, comprobantes)
        
        # Procesar resultados
        encontrados = []
        no_encontrados = []
        errores = []
        
        for resultado in resultados:
            cbte = resultado['comprobante']
            cbte_str = f"Tipo {cbte['tipo']} PV{cbte['punto_venta']} #{cbte['numero']}"
            
            if resultado['success']:
                if resultado['datos']:
                    encontrados.append((cbte_str, resultado['datos']))
                else:
                    no_encontrados.append(cbte_str)
            else:
                errores.append((cbte_str, resultado['error']))
        
        print(f"\n📊 RESUMEN:")
        print(f"✅ Encontrados: {len(encontrados)}")
        print(f"📭 No encontrados: {len(no_encontrados)}")
        print(f"❌ Errores: {len(errores)}")
        
        # Mostrar encontrados
        if encontrados:
            print(f"\n✅ COMPROBANTES ENCONTRADOS:")
            for cbte_str, datos in encontrados:
                print(f"   {cbte_str} - Total: ${datos.get('importe_total')}")
        
        return encontrados
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def ejemplo_exportacion():
    """Ejemplo: exportar datos de comprobante"""
    print("\n📋 === EJEMPLO 4: EXPORTACIÓN ===")
    
    try:
        # Consultar un comprobante
        cuit = "20321518045" 
        
        datos = consulta_rapida_wsmtxca(
            cuit=cuit,
            tipo=1,
            punto_venta=1,
            numero=1,
            ambiente='prod'
        )
        
        if datos:
            client = crear_cliente_wsmtxca(ambiente='prod')
            
            # Exportar en ambos formatos
            archivo_json = client.exportar_comprobante(datos, 'json')
            archivo_csv = client.exportar_comprobante(datos, 'csv')
            
            print(f"📄 Exportado JSON: {archivo_json}")
            print(f"📊 Exportado CSV: {archivo_csv}")
            
            return archivo_json, archivo_csv
        else:
            print("📭 No hay datos para exportar")
            return None, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

def ejemplo_busqueda_sistemática():
    """Ejemplo: búsqueda sistemática en puntos de venta"""
    print("\n📋 === EJEMPLO 5: BÚSQUEDA SISTEMÁTICA ===")
    
    try:
        cuit = "20321518045"
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        # Tipos principales a probar
        tipos_principales = [1, 6, 11, 51, 52, 53]  # A, B, C, M, NDM, NCM
        puntos_venta = [1, 2, 3, 4]  # Puntos de venta comunes
        
        encontrados_total = 0
        
        for pv in puntos_venta:
            print(f"\n🏪 === PUNTO DE VENTA {pv} ===")
            
            for tipo in tipos_principales:
                # Solo probar los primeros 3 números por tipo/PV
                for numero in range(1, 4):
                    try:
                        resultado = client.consultar_comprobante(
                            cuit_representada=cuit,
                            tipo_comprobante=tipo,
                            punto_venta=pv,
                            numero_comprobante=numero
                        )
                        
                        if resultado:
                            encontrados_total += 1
                            print(f"   ✅ Tipo {tipo} #{numero}: ${resultado.get('importe_total')} ({resultado.get('fecha_emision')})")
                            
                            # Solo mostrar detalles del primero encontrado por tipo
                            if numero == 1:
                                items = resultado.get('items', [])
                                if items:
                                    print(f"      📦 {len(items)} items con códigos MTX")
                        
                    except Exception as e:
                        if "602" not in str(e):  # Ignorar "no existe"
                            print(f"   ⚠️ Tipo {tipo} #{numero}: {e}")
        
        print(f"\n🎉 TOTAL ENCONTRADOS: {encontrados_total} comprobantes")
        return encontrados_total
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

def ejemplo_analisis_items_mtx():
    """Ejemplo: análisis de códigos MTX en items"""
    print("\n📋 === EJEMPLO 6: ANÁLISIS CÓDIGOS MTX ===")
    
    try:
        # Este ejemplo requiere que haya comprobantes con items
        cuit = "20321518045"
        
        comprobantes_con_items = []
        
        # Buscar comprobantes que tengan items
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        for tipo in [1, 6, 51]:  # Principales tipos
            for numero in range(1, 6):
                try:
                    resultado = client.consultar_comprobante(
                        cuit_representada=cuit,
                        tipo_comprobante=tipo,
                        punto_venta=1,
                        numero_comprobante=numero
                    )
                    
                    if resultado and resultado.get('items'):
                        comprobantes_con_items.append(resultado)
                        
                except:
                    continue
        
        if not comprobantes_con_items:
            print("📭 No se encontraron comprobantes con items para analizar")
            return
        
        print(f"📦 Analizando {len(comprobantes_con_items)} comprobantes con items...")
        
        # Análisis de códigos MTX
        codigos_mtx = {}
        total_items = 0
        
        for cbte in comprobantes_con_items:
            items = cbte.get('items', [])
            total_items += len(items)
            
            for item in items:
                codigo = item.get('codigo_mtx')
                descripcion = item.get('descripcion')
                
                if codigo:
                    if codigo not in codigos_mtx:
                        codigos_mtx[codigo] = {
                            'descripcion': descripcion,
                            'cantidad_usos': 0,
                            'total_importe': 0
                        }
                    
                    codigos_mtx[codigo]['cantidad_usos'] += 1
                    try:
                        importe = float(item.get('importe_total', 0))
                        codigos_mtx[codigo]['total_importe'] += importe
                    except:
                        pass
        
        print(f"\n📊 ANÁLISIS MTX:")
        print(f"   Total items analizados: {total_items}")
        print(f"   Códigos MTX únicos: {len(codigos_mtx)}")
        
        if codigos_mtx:
            print(f"\n🏷️ TOP CÓDIGOS MTX:")
            sorted_codigos = sorted(codigos_mtx.items(), 
                                  key=lambda x: x[1]['cantidad_usos'], 
                                  reverse=True)
            
            for codigo, info in sorted_codigos[:10]:
                print(f"   {codigo}: {info['descripcion']} ({info['cantidad_usos']} usos, ${info['total_importe']:.2f})")
        
        return codigos_mtx
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}

def ejecutar_todos_los_ejemplos():
    """Ejecutar todos los ejemplos en secuencia"""
    print("🚀 === EJECUTANDO TODOS LOS EJEMPLOS WSMTXCA ===")
    print("Este proceso puede tomar varios minutos...\n")
    
    ejemplos = [
        ("Consulta Básica", ejemplo_consulta_basica),
        ("Facturas Monotributo", ejemplo_consulta_monotributo),
        ("Consulta Múltiple", ejemplo_consulta_multiple),
        ("Exportación", ejemplo_exportacion),
        ("Búsqueda Sistemática", ejemplo_busqueda_sistemática),
        ("Análisis Códigos MTX", ejemplo_analisis_items_mtx)
    ]
    
    resultados = {}
    
    for nombre, funcion in ejemplos:
        print(f"\n{'='*60}")
        print(f"Ejecutando: {nombre}")
        print(f"{'='*60}")
        
        try:
            resultado = funcion()
            resultados[nombre] = {'success': True, 'resultado': resultado}
        except Exception as e:
            print(f"❌ Error en {nombre}: {e}")
            resultados[nombre] = {'success': False, 'error': str(e)}
    
    # Resumen final
    print(f"\n🎉 === RESUMEN FINAL ===")
    exitosos = sum(1 for r in resultados.values() if r['success'])
    print(f"Ejemplos exitosos: {exitosos}/{len(ejemplos)}")
    
    for nombre, resultado in resultados.items():
        status = "✅" if resultado['success'] else "❌"
        print(f"   {status} {nombre}")
    
    return resultados

if __name__ == "__main__":
    print("🧪 === EJEMPLOS WSMTXCA ===")
    print("Seleccione qué ejemplo ejecutar:")
    print("1. Consulta básica")
    print("2. Facturas monotributo") 
    print("3. Consulta múltiple")
    print("4. Exportación")
    print("5. Búsqueda sistemática")
    print("6. Análisis códigos MTX")
    print("7. Ejecutar todos")
    print("0. Salir")
    
    try:
        opcion = input("\nOpción (1-7, 0 para salir): ").strip()
        
        if opcion == "1":
            ejemplo_consulta_basica()
        elif opcion == "2":
            ejemplo_consulta_monotributo()
        elif opcion == "3":
            ejemplo_consulta_multiple()
        elif opcion == "4":
            ejemplo_exportacion()
        elif opcion == "5":
            ejemplo_busqueda_sistemática()
        elif opcion == "6":
            ejemplo_analisis_items_mtx()
        elif opcion == "7":
            ejecutar_todos_los_ejemplos()
        elif opcion == "0":
            print("👋 ¡Hasta luego!")
        else:
            print("❌ Opción inválida")
            
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error: {e}")