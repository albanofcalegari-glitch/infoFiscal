#!/usr/bin/env python3
"""
EXTRACTOR COMPLETO DE FACTURAS WSFEv1
=====================================

Implementa la secuencia completa para obtener TODAS las facturas de un CUIT:
1. FEParamGetPtosVenta() - Obtener puntos de venta
2. FEParamGetTiposCbte() - Obtener tipos de comprobantes  
3. FECompUltimoAutorizado() - Último número por punto/tipo
4. FECompConsultar() - Consultar cada comprobante individual

Con manejo robusto de errores y rate limiting.
"""

import sys
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append('src')
from wsfev1_client import WSFEv1Client

class ExtractorCompletaFacturas:
    """Extractor completo de facturas WSFEv1"""
    
    def __init__(self, cert_path='certs/certificado.crt', key_path='certs/clave_privada.key', 
                 ambiente='prod', rate_limit_delay=0.5, max_workers=3):
        """
        Inicializar extractor
        
        Args:
            cert_path: Ruta al certificado
            key_path: Ruta a la clave privada  
            ambiente: 'prod' o 'homologacion'
            rate_limit_delay: Delay entre consultas (segundos)
            max_workers: Máximo threads concurrentes
        """
        self.client = WSFEv1Client(cert_path, key_path, ambiente)
        self.rate_limit_delay = rate_limit_delay
        self.max_workers = max_workers
        self.estadisticas = {
            'puntos_venta': 0,
            'tipos_comprobante': 0,
            'combinaciones_probadas': 0,
            'facturas_encontradas': 0,
            'errores': 0,
            'tiempo_inicio': None,
            'tiempo_fin': None
        }
        self._lock = threading.Lock()
        
    def obtener_todas_las_facturas(self, cuit, tipos_incluir=None, puntos_incluir=None, 
                                  limite_por_tipo=None, mostrar_progreso=True):
        """
        Obtener TODAS las facturas de un CUIT siguiendo la secuencia completa
        
        Args:
            cuit: CUIT del contribuyente
            tipos_incluir: Lista de tipos a incluir (None = todos)
            puntos_incluir: Lista de puntos a incluir (None = todos)
            limite_por_tipo: Máximo de facturas por tipo/punto (None = todas)
            mostrar_progreso: Mostrar progreso en consola
            
        Returns:
            dict: {
                'facturas': [lista de facturas],
                'estadisticas': estadísticas del proceso,
                'resumen': resumen por punto y tipo
            }
        """
        self.estadisticas['tiempo_inicio'] = datetime.now()
        
        if mostrar_progreso:
            print("🚀 EXTRACCIÓN COMPLETA DE FACTURAS WSFEv1")
            print("=" * 60)
            print(f"🎯 CUIT: {cuit}")
            print(f"🌐 Ambiente: {self.client.ambiente}")
            print(f"⏱️  Rate Limit: {self.rate_limit_delay}s")
            print(f"👥 Workers: {self.max_workers}")
            print("=" * 60)
        
        try:
            # PASO 1: Obtener puntos de venta
            if mostrar_progreso:
                print("\n1️⃣ OBTENIENDO PUNTOS DE VENTA...")
            puntos_venta = self._obtener_puntos_venta(cuit, puntos_incluir, mostrar_progreso)
            
            if not puntos_venta:
                print("❌ No se encontraron puntos de venta habilitados")
                return {'facturas': [], 'estadisticas': self.estadisticas, 'resumen': {}}
            
            # PASO 2: Obtener tipos de comprobantes
            if mostrar_progreso:
                print("\n2️⃣ OBTENIENDO TIPOS DE COMPROBANTES...")
            tipos_comprobante = self._obtener_tipos_comprobante(cuit, tipos_incluir, mostrar_progreso)
            
            if not tipos_comprobante:
                print("❌ No se encontraron tipos de comprobante")
                return {'facturas': [], 'estadisticas': self.estadisticas, 'resumen': {}}
            
            # PASO 3: Obtener últimos autorizados por combinación
            if mostrar_progreso:
                print("\n3️⃣ OBTENIENDO ÚLTIMOS AUTORIZADOS...")
            combinaciones = self._obtener_ultimos_autorizados(cuit, puntos_venta, tipos_comprobante, mostrar_progreso)
            
            # PASO 4: Extraer todas las facturas
            if mostrar_progreso:
                print("\n4️⃣ EXTRAYENDO FACTURAS...")
            todas_las_facturas = self._extraer_todas_las_facturas(cuit, combinaciones, limite_por_tipo, mostrar_progreso)
            
            # Generar resumen
            resumen = self._generar_resumen(todas_las_facturas, puntos_venta, tipos_comprobante)
            
            self.estadisticas['tiempo_fin'] = datetime.now()
            
            if mostrar_progreso:
                self._mostrar_estadisticas_finales()
            
            return {
                'facturas': todas_las_facturas,
                'estadisticas': self.estadisticas,
                'resumen': resumen
            }
            
        except Exception as e:
            print(f"❌ ERROR GENERAL: {e}")
            self.estadisticas['tiempo_fin'] = datetime.now()
            return {'facturas': [], 'estadisticas': self.estadisticas, 'resumen': {}}
    
    def _obtener_puntos_venta(self, cuit, puntos_incluir, mostrar_progreso):
        """PASO 1: Obtener puntos de venta usando FEParamGetPtosVenta"""
        try:
            puntos_raw = self.client.obtener_puntos_venta(cuit)
            
            if not puntos_raw:
                if mostrar_progreso:
                    print("   ❌ No hay puntos de venta disponibles")
                return []
            
            # Filtrar puntos si se especifica
            if puntos_incluir:
                puntos_filtrados = [p for p in puntos_raw if p.get('numero') in puntos_incluir]
            else:
                puntos_filtrados = puntos_raw
            
            self.estadisticas['puntos_venta'] = len(puntos_filtrados)
            
            if mostrar_progreso:
                print(f"   ✅ Encontrados: {len(puntos_filtrados)} puntos de venta")
                for punto in puntos_filtrados[:5]:  # Mostrar primeros 5
                    print(f"      • Punto {punto.get('numero', 'N/A')}: {punto.get('descripcion', 'Sin descripción')}")
                if len(puntos_filtrados) > 5:
                    print(f"      • ... y {len(puntos_filtrados)-5} más")
            
            return puntos_filtrados
            
        except Exception as e:
            if mostrar_progreso:
                print(f"   ❌ Error obteniendo puntos de venta: {e}")
            return []
    
    def _obtener_tipos_comprobante(self, cuit, tipos_incluir, mostrar_progreso):
        """PASO 2: Obtener tipos de comprobantes usando FEParamGetTiposCbte"""
        try:
            tipos_raw = self.client.obtener_tipos_comprobante(cuit)
            
            if not tipos_raw:
                if mostrar_progreso:
                    print("   ❌ No hay tipos de comprobante disponibles")
                return []
            
            # Filtrar tipos si se especifica
            if tipos_incluir:
                tipos_filtrados = [t for t in tipos_raw if t.get('id') in tipos_incluir]
            else:
                tipos_filtrados = tipos_raw
            
            self.estadisticas['tipos_comprobante'] = len(tipos_filtrados)
            
            if mostrar_progreso:
                print(f"   ✅ Encontrados: {len(tipos_filtrados)} tipos de comprobante")
                for tipo in tipos_filtrados[:5]:  # Mostrar primeros 5
                    print(f"      • Tipo {tipo.get('id', 'N/A')}: {tipo.get('descripcion', 'Sin descripción')}")
                if len(tipos_filtrados) > 5:
                    print(f"      • ... y {len(tipos_filtrados)-5} más")
            
            return tipos_filtrados
            
        except Exception as e:
            if mostrar_progreso:
                print(f"   ❌ Error obteniendo tipos de comprobante: {e}")
            return []
    
    def _obtener_ultimos_autorizados(self, cuit, puntos_venta, tipos_comprobante, mostrar_progreso):
        """PASO 3: Obtener últimos autorizados usando FECompUltimoAutorizado"""
        combinaciones = []
        total_combinaciones = len(puntos_venta) * len(tipos_comprobante)
        procesadas = 0
        
        if mostrar_progreso:
            print(f"   🔍 Probando {total_combinaciones} combinaciones punto/tipo...")
        
        for punto in puntos_venta:
            punto_numero = punto.get('numero')
            
            for tipo in tipos_comprobante:
                tipo_id = tipo.get('id')
                
                try:
                    # Aplicar rate limiting
                    if self.rate_limit_delay > 0:
                        time.sleep(self.rate_limit_delay)
                    
                    ultimo = self.client.obtener_ultimo_comprobante(cuit, tipo_id, punto_numero)
                    
                    if ultimo and ultimo > 0:
                        combinaciones.append({
                            'punto_venta': punto_numero,
                            'tipo_comprobante': tipo_id,
                            'ultimo_autorizado': ultimo,
                            'punto_info': punto,
                            'tipo_info': tipo
                        })
                        
                        if mostrar_progreso:
                            tipo_desc = tipo.get('descripcion', f'Tipo {tipo_id}')[:20]
                            print(f"      ✅ P{punto_numero} - {tipo_desc}: #{ultimo}")
                    
                    procesadas += 1
                    self.estadisticas['combinaciones_probadas'] = procesadas
                    
                    if mostrar_progreso and procesadas % 10 == 0:
                        progreso = (procesadas / total_combinaciones) * 100
                        print(f"      📊 Progreso: {procesadas}/{total_combinaciones} ({progreso:.1f}%)")
                    
                except Exception as e:
                    with self._lock:
                        self.estadisticas['errores'] += 1
                    if mostrar_progreso and "error" in str(e).lower():
                        print(f"      ⚠️ P{punto_numero}-T{tipo_id}: {str(e)[:30]}...")
        
        if mostrar_progreso:
            print(f"   📊 Resultado: {len(combinaciones)} combinaciones con facturas")
        
        return combinaciones
    
    def _extraer_todas_las_facturas(self, cuit, combinaciones, limite_por_tipo, mostrar_progreso):
        """PASO 4: Extraer facturas usando FECompConsultar"""
        todas_las_facturas = []
        total_facturas_esperadas = sum(comb['ultimo_autorizado'] for comb in combinaciones)
        
        if limite_por_tipo:
            total_facturas_esperadas = min(total_facturas_esperadas, 
                                         len(combinaciones) * limite_por_tipo)
        
        if mostrar_progreso:
            print(f"   🎯 Facturas esperadas: ~{total_facturas_esperadas}")
            print(f"   👥 Usando {self.max_workers} workers concurrentes")
        
        # Usar ThreadPoolExecutor para consultas concurrentes
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Preparar tareas
            tareas = []
            
            for combinacion in combinaciones:
                punto = combinacion['punto_venta']
                tipo = combinacion['tipo_comprobante']
                ultimo = combinacion['ultimo_autorizado']
                
                # Determinar rango a consultar
                fin_rango = limite_por_tipo if limite_por_tipo else ultimo
                fin_rango = min(fin_rango, ultimo)
                
                for numero in range(1, fin_rango + 1):
                    tarea = executor.submit(
                        self._consultar_comprobante_seguro, 
                        cuit, punto, tipo, numero, combinacion
                    )
                    tareas.append(tarea)
            
            # Procesar resultados
            facturas_procesadas = 0
            for tarea in as_completed(tareas):
                try:
                    factura = tarea.result()
                    if factura:
                        todas_las_facturas.append(factura)
                        with self._lock:
                            self.estadisticas['facturas_encontradas'] += 1
                    
                    facturas_procesadas += 1
                    
                    if mostrar_progreso and facturas_procesadas % 50 == 0:
                        encontradas = len(todas_las_facturas)
                        progreso = (facturas_procesadas / len(tareas)) * 100
                        print(f"      📊 Progreso: {facturas_procesadas}/{len(tareas)} "
                              f"({progreso:.1f}%) | Encontradas: {encontradas}")
                
                except Exception as e:
                    with self._lock:
                        self.estadisticas['errores'] += 1
        
        if mostrar_progreso:
            print(f"   ✅ Extracción completada: {len(todas_las_facturas)} facturas")
        
        return todas_las_facturas
    
    def _consultar_comprobante_seguro(self, cuit, punto, tipo, numero, combinacion_info):
        """Consultar un comprobante individual con manejo de errores"""
        try:
            # Rate limiting por thread
            if self.rate_limit_delay > 0:
                time.sleep(self.rate_limit_delay)
            
            factura = self.client.consultar_comprobante(cuit, tipo, punto, numero)
            
            if factura and isinstance(factura, dict):
                # Enriquecer con información adicional
                factura.update({
                    'punto_venta_info': combinacion_info['punto_info'],
                    'tipo_comprobante_info': combinacion_info['tipo_info'],
                    'fecha_extraccion': datetime.now().isoformat(),
                    'cuit_emisor': cuit
                })
                return factura
            
            return None
            
        except Exception as e:
            # Manejar errores silenciosamente (facturas inexistentes son normales)
            if "not found" not in str(e).lower():
                with self._lock:
                    self.estadisticas['errores'] += 1
            return None
    
    def _generar_resumen(self, facturas, puntos_venta, tipos_comprobante):
        """Generar resumen de la extracción"""
        resumen = {
            'total_facturas': len(facturas),
            'por_punto_venta': {},
            'por_tipo_comprobante': {},
            'por_fecha': {},
            'importes': {
                'total_general': 0,
                'promedio': 0,
                'maximo': 0,
                'minimo': float('inf')
            }
        }
        
        # Resumen por punto de venta
        for punto in puntos_venta:
            punto_num = punto.get('numero')
            facturas_punto = [f for f in facturas if f.get('PtoVta') == str(punto_num)]
            resumen['por_punto_venta'][punto_num] = {
                'cantidad': len(facturas_punto),
                'descripcion': punto.get('descripcion', 'Sin descripción')
            }
        
        # Resumen por tipo de comprobante
        for tipo in tipos_comprobante:
            tipo_id = tipo.get('id')
            facturas_tipo = [f for f in facturas if f.get('CbteTipo') == str(tipo_id)]
            resumen['por_tipo_comprobante'][tipo_id] = {
                'cantidad': len(facturas_tipo),
                'descripcion': tipo.get('descripcion', 'Sin descripción')
            }
        
        # Calcular importes
        importes_validos = []
        for factura in facturas:
            try:
                importe = float(factura.get('ImpTotal', 0))
                if importe > 0:
                    importes_validos.append(importe)
            except (ValueError, TypeError):
                continue
        
        if importes_validos:
            resumen['importes']['total_general'] = sum(importes_validos)
            resumen['importes']['promedio'] = sum(importes_validos) / len(importes_validos)
            resumen['importes']['maximo'] = max(importes_validos)
            resumen['importes']['minimo'] = min(importes_validos)
        
        return resumen
    
    def _mostrar_estadisticas_finales(self):
        """Mostrar estadísticas finales del proceso"""
        tiempo_total = self.estadisticas['tiempo_fin'] - self.estadisticas['tiempo_inicio']
        
        print("\n" + "=" * 60)
        print("📊 ESTADÍSTICAS FINALES")
        print("=" * 60)
        print(f"⏱️  Tiempo total: {tiempo_total}")
        print(f"📍 Puntos de venta: {self.estadisticas['puntos_venta']}")
        print(f"📋 Tipos de comprobante: {self.estadisticas['tipos_comprobante']}")
        print(f"🔍 Combinaciones probadas: {self.estadisticas['combinaciones_probadas']}")
        print(f"✅ Facturas encontradas: {self.estadisticas['facturas_encontradas']}")
        print(f"❌ Errores: {self.estadisticas['errores']}")
        
        if tiempo_total.total_seconds() > 0:
            facturas_por_segundo = self.estadisticas['facturas_encontradas'] / tiempo_total.total_seconds()
            print(f"⚡ Velocidad: {facturas_por_segundo:.2f} facturas/segundo")

def extraer_facturas_completas(cuit, tipos_incluir=None, puntos_incluir=None, 
                              limite_por_tipo=None, mostrar_progreso=True):
    """
    Función conveniente para extraer todas las facturas de un CUIT
    
    Args:
        cuit: CUIT del contribuyente
        tipos_incluir: Lista de tipos a incluir [1, 6, 11] (None = todos)
        puntos_incluir: Lista de puntos a incluir [1, 2, 3] (None = todos)  
        limite_por_tipo: Máximo facturas por combinación (None = todas)
        mostrar_progreso: Mostrar progreso en consola
        
    Returns:
        dict: Resultado completo con facturas, estadísticas y resumen
    """
    extractor = ExtractorCompletaFacturas(
        cert_path='certs/certificado.crt',
        key_path='certs/clave_privada.key', 
        ambiente='prod',
        rate_limit_delay=0.3,  # Ajustable según necesidad
        max_workers=5          # Ajustable según capacidad
    )
    
    return extractor.obtener_todas_las_facturas(
        cuit=cuit,
        tipos_incluir=tipos_incluir,
        puntos_incluir=puntos_incluir,
        limite_por_tipo=limite_por_tipo,
        mostrar_progreso=mostrar_progreso
    )

if __name__ == "__main__":
    # Ejemplo de uso
    print("🧪 EJEMPLO DE EXTRACCIÓN COMPLETA")
    print("=" * 50)
    
    cuit_ejemplo = input("📋 Ingresá el CUIT a extraer: ").strip()
    
    if len(cuit_ejemplo) == 11 and cuit_ejemplo.isdigit():
        # Extraer solo primeras 5 facturas por tipo para prueba
        resultado = extraer_facturas_completas(
            cuit=cuit_ejemplo,
            tipos_incluir=[1, 6, 11],  # Solo A, B, C
            limite_por_tipo=5,         # Máximo 5 por tipo
            mostrar_progreso=True
        )
        
        print(f"\n🎯 RESULTADO:")
        print(f"📄 Facturas encontradas: {len(resultado['facturas'])}")
        print(f"📊 Ver resultado['resumen'] para detalles completos")
        
    else:
        print("❌ CUIT inválido. Debe tener 11 dígitos.")