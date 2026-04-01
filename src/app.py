# -*- coding: utf-8 -*-

# --- IMPORTS OPTIMIZADOS ---
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, flash
from pathlib import Path
import os

# Cargar variables de entorno del archivo .env
try:
    from dotenv import load_dotenv
    # Cargar .env desde el directorio padre (donde está el .env)
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"Archivo .env cargado desde: {env_path}")
    print(f"INFOFISCAL_MODE: {os.environ.get('INFOFISCAL_MODE', 'No configurado')}")
except ImportError:
    print("python-dotenv no disponible")

# Configurar rutas absolutas para templates y static
import os
template_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')

app = Flask(__name__, 
           template_folder=template_folder,
           static_folder=static_folder)
app.secret_key = 'cambia-esto-por-una-clave-segura'

# Cache para conexiones de BD
_db_connection_cache = None

def get_db_connection():
    """Obtener conexión d                    cursor.execute('UPDATE usuario SET cantidadDeIntentos = ? WHERE usuario = ?', (intentos, usuario))
                    error = f'Contraseña incorrecta. Intento {intentos} de 5.'
                conn.commit() reutilizable"""
    global _db_connection_cache
    
    # Verificar si la conexión existe y está válida
    if _db_connection_cache is not None:
        try:
            # Test rápido para ver si la conexión funciona
            _db_connection_cache.execute('SELECT 1')
            return _db_connection_cache
        except:
            # Conexión cerrada o inválida, crear nueva
            _db_connection_cache = None
    
    # Crear nueva conexión
    if _db_connection_cache is None:
        import sqlite3
        db_path = Path(__file__).parent.parent / 'infofiscal.db'
        _db_connection_cache = sqlite3.connect(str(db_path), check_same_thread=False)
        _db_connection_cache.row_factory = sqlite3.Row
        
    return _db_connection_cache

def get_bcrypt():
    """Lazy import de bcrypt"""
    import bcrypt
    return bcrypt

"""Endpoint actualizado: descarga/enumeración estructurada de comprobantes AFIP
Devuelve estados claros:
  no_puntos_venta -> habilitar PV en AFIP (error 602)
  sin_comprobantes -> hay PV pero aún no se emitieron comprobantes (FECompUltimoAutorizado=0)
  ok -> enumeración exitosa (puede haber 0 nuevos guardados si ya existían)
  error -> fallo general
Parámetros query:
  cuit=<CUIT Objetivo>
  max_por_tipo (opcional, default 3)
"""
@app.route('/descargar-facturas')
def descargar_facturas():
    """
    Endpoint actualizado: Descarga comprobantes AFIP usando afip_extract_by_date.py
    
    Parámetros:
    - cuit: CUIT objetivo (requerido)
    - desde: Fecha desde YYYY-MM-DD (opcional, default: último mes)
    - hasta: Fecha hasta YYYY-MM-DD (opcional, default: hoy)
    - incluir_tipos: Tipos a incluir separados por coma (opcional)
    - excluir_tipos: Tipos a excluir separados por coma (opcional)
    """
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    cuit = request.args.get('cuit')
    if not cuit:
        return jsonify({'success': False, 'error': 'CUIT requerido'}), 400

    # Pre-chequeos
    modo_produccion = os.environ.get('INFOFISCAL_MODE') == 'production'
    if not modo_produccion:
        return jsonify({'success': False,'error': 'Aplicación no está en modo producción','detalle': 'Configure INFOFISCAL_MODE=production'}), 400
    
    # Verificar certificados usando rutas absolutas
    from pathlib import Path
    if os.path.basename(os.getcwd()) == 'src':
        base_dir = Path(os.getcwd()).parent
    else:
        base_dir = Path(os.getcwd())
    
    cert_path = base_dir / 'certs' / 'certificado.crt'
    key_path = base_dir / 'certs' / 'clave_privada.key'
    
    if not (cert_path.exists() and key_path.exists()):
        return jsonify({'success': False,'error': 'Certificados AFIP no encontrados','detalle': f'Verifique {cert_path} y {key_path}'}), 400

    try:
        # Parsear fechas (default: último mes)
        from datetime import datetime, timedelta
        
        hasta_str = request.args.get('hasta')
        desde_str = request.args.get('desde')
        
        if hasta_str:
            hasta = datetime.strptime(hasta_str, '%Y-%m-%d')
        else:
            hasta = datetime.now()
        
        if desde_str:
            desde = datetime.strptime(desde_str, '%Y-%m-%d')
        else:
            desde = hasta - timedelta(days=30)  # Último mes por default
        
        # Parsear tipos de comprobante
        incluir_tipos = []
        excluir_tipos = []
        
        if request.args.get('incluir_tipos'):
            incluir_tipos = [int(x.strip()) for x in request.args.get('incluir_tipos').split(',') if x.strip().isdigit()]
        
        if request.args.get('excluir_tipos'):
            excluir_tipos = [int(x.strip()) for x in request.args.get('excluir_tipos').split(',') if x.strip().isdigit()]

        # Configurar variables de entorno temporalmente para afip_extract_by_date
        consultor_cuit = os.environ.get('AFIP_CONSULTOR_CUIT', '20321518045')
        
        # Setear variables para afip_extract_by_date
        os.environ['AFIP_ENV'] = 'prod' if modo_produccion else 'homo'
        os.environ['AFIP_CUIT'] = consultor_cuit
        os.environ['AFIP_CERT_PATH'] = 'certs/certificado.crt'
        os.environ['AFIP_KEY_PATH'] = 'certs/clave_privada.key'
        
        print(f"🔧 Descargando facturas AFIP para CUIT {cuit} desde {desde.date()} hasta {hasta.date()}")
        
        # Importar y ejecutar la función principal de afip_extract_by_date
        import sys
        
        # Agregar el directorio raíz al path para importar afip_extract_by_date
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        
        # Importar módulos simplificados (sin zeep/lxml)
        from afip_simple import extraer_facturas_simple, export_simple
        
        # PASO 1: Extracción directa con método simplificado
        try:
            comprobantes = extraer_facturas_simple(
                cuit=cuit,  # CUIT del cliente a consultar
                cuit_consultor=consultor_cuit,  # CUIT del consultor para autenticación
                desde=desde.strftime('%Y-%m-%d'),
                hasta=hasta.strftime('%Y-%m-%d'),
                cert_path=str(cert_path),
                key_path=str(key_path)
            )
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Error extrayendo comprobantes',
                'detalle': str(e)
            }), 500
        
        # PASO 2: Exportación
        try:
            # Crear directorio de salida
            facturas_dir = Path(__file__).parent.parent / 'facturas'
            facturas_dir.mkdir(exist_ok=True)
            
            # Nombre de archivos basado en CUIT y fecha
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"facturas_{cuit}_{timestamp}"
            
            archivos = export_simple(comprobantes, str(facturas_dir / base_filename))
            
            # Convertir paths absolutos a relativos para el frontend
            csv_rel = Path(archivos['csv']).relative_to(Path(__file__).parent.parent)
            json_rel = Path(archivos['json']).relative_to(Path(__file__).parent.parent)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Error exportando archivos',
                'detalle': str(e)
            }), 500
        
        # Determinar mensaje y tipo según resultados
        if len(comprobantes) == 0:
            user_message = 'El cliente seleccionado no posee facturas electrónicas en el rango de fechas especificado.'
            tipo_alerta = 'info'
            accion_sugerida = f'No se encontraron facturas entre {desde.date()} y {hasta.date()}'
            success = True
        else:
            user_message = f'Se encontraron {len(comprobantes)} facturas electrónicas.'
            tipo_alerta = 'success'
            accion_sugerida = f'Archivos generados: CSV ({len(comprobantes)} filas) y JSON completo'
            success = True
        
        # Respuesta exitosa
        payload = {
            'success': success,
            'status': 'ok' if len(comprobantes) > 0 else 'sin_facturas',
            'user_message': user_message,
            'tipo_alerta': tipo_alerta,
            'accion_sugerida': accion_sugerida,
            'cuit_objetivo': cuit,
            'fecha_desde': desde.strftime('%Y-%m-%d'),
            'fecha_hasta': hasta.strftime('%Y-%m-%d'),
            'total_encontrados': len(comprobantes),
            'archivos_generados': {
                'csv': str(csv_rel),
                'json': str(json_rel)
            },
            'resumen': {
                'cantidad_total': len(comprobantes),
                'periodo': f"{desde.date()} a {hasta.date()}",
                'tipos_consultados': incluir_tipos if incluir_tipos else 'Todos',
                'tipos_excluidos': excluir_tipos if excluir_tipos else 'Ninguno'
            }
        }
        
        return jsonify(payload), 200
        
    except Exception as e:
        print(f"❌ Error en descargar_facturas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Error interno del servidor',
            'detalle': str(e)
        }), 500

@app.route('/buscar-wsmtxca-completo')
def buscar_wsmtxca_completo():
    """Buscar todos los tipos de comprobantes WSMTXCA para un CUIT"""
    try:
        # Obtener parámetros
        cuit = request.args.get('cuit', '').strip()
        punto_venta = request.args.get('punto_venta', '').strip()
        limite = int(request.args.get('limite', 25))
        
        # Validar parámetros requeridos
        if not cuit:
            return jsonify({
                'success': False,
                'error': 'CUIT es requerido'
            }), 400
        
        # Validar CUIT
        cuit_clean = cuit.replace('-', '').replace(' ', '')
        if not cuit_clean.isdigit() or len(cuit_clean) != 11:
            return jsonify({
                'success': False,
                'error': 'CUIT debe tener 11 dígitos numéricos'
            }), 400
        
        # Importar cliente WSMTXCA
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from wsmtxca_client import WSMTXCAClient
        
        # Configurar rutas de certificados
        cert_path = Path(__file__).parent.parent / 'certs' / 'certificado.crt'
        key_path = Path(__file__).parent.parent / 'certs' / 'clave_privada.key'
        
        # Crear cliente WSMTXCA
        cliente = WSMTXCAClient(str(cert_path), str(key_path))
        
        # Tipos de comprobante principales a consultar (más comunes)
        tipos_principales = [11, 51, 1, 6]  # Factura C, M, A, B (orden por frecuencia)
        tipos_secundarios = [2, 3, 7, 8, 52, 53, 201, 206]  # Notas y FCE
        
        # Puntos de venta a consultar (limitado para eficiencia)
        if punto_venta:
            puntos_venta = [int(punto_venta)]
        else:
            puntos_venta = [1, 2]  # Solo PV 1 y 2 por defecto (más comunes)
        
        resultados = []
        max_consultas = 100  # Límite de seguridad
        consultas_realizadas = 0
        
        # Función auxiliar para consultar un rango
        def consultar_rango(tipo, pv, inicio, fin):
            nonlocal consultas_realizadas
            encontrados_consecutivos = 0
            no_encontrados_consecutivos = 0
            
            for num in range(inicio, fin + 1):
                if consultas_realizadas >= max_consultas:
                    break
                    
                try:
                    consultas_realizadas += 1
                    resultado = cliente.consultar_comprobante(
                        cuit=cuit_clean,
                        tipo=tipo,
                        punto_venta=pv,
                        numero=num
                    )
                    
                    resultado['consulta'] = {
                        'cuit': cuit_clean,
                        'tipo': tipo,
                        'punto_venta': pv,
                        'numero': num
                    }
                    
                    if resultado['status'] == 'encontrado':
                        encontrados_consecutivos += 1
                        no_encontrados_consecutivos = 0
                        resultados.append(resultado)
                    else:
                        no_encontrados_consecutivos += 1
                        # Si hay muchos no encontrados seguidos, parar
                        if no_encontrados_consecutivos >= 5:
                            break
                            
                except Exception as e:
                    no_encontrados_consecutivos += 1
                    if no_encontrados_consecutivos >= 3:
                        break
        
        # Consultar tipos principales primero
        for tipo in tipos_principales:
            if consultas_realizadas >= max_consultas:
                break
            for pv in puntos_venta:
                if consultas_realizadas >= max_consultas:
                    break
                consultar_rango(tipo, pv, 1, min(limite, 20))
        
        # Si encontramos resultados, consultar tipos secundarios
        if resultados:
            for tipo in tipos_secundarios:
                if consultas_realizadas >= max_consultas:
                    break
                for pv in puntos_venta:
                    if consultas_realizadas >= max_consultas:
                        break
                    consultar_rango(tipo, pv, 1, min(10, limite//2))
        
        # Filtrar solo los encontrados para el resumen
        encontrados = [r for r in resultados if r['status'] == 'encontrado']
        
        return jsonify({
            'success': True,
            'cuit': cuit_clean,
            'consultas_realizadas': consultas_realizadas,
            'total_encontrados': len(encontrados),
            'resultados': resultados,
            'puntos_venta_consultados': puntos_venta,
            'limite_aplicado': limite
        })
        
    except Exception as e:
        print(f"Error en buscar_wsmtxca_completo: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Error interno del servidor',
            'detalle': str(e)
        }), 500

@app.route('/buscar-cliente', methods=['POST'])
def buscar_cliente():
    """Buscar cliente en la base de datos"""
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401

    try:
        # Obtener datos del formulario o JSON
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            busqueda = data.get('search', '').strip() if data else ''
        else:
            # Datos de formulario
            busqueda = request.form.get('busqueda', '').strip()

        if not busqueda:
            return jsonify({'success': False, 'error': 'Parámetro de búsqueda requerido'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Búsqueda más flexible
        print(f"DEBUG: Buscando cliente con término: '{busqueda}'")
        if len(busqueda) == 11 and busqueda.isdigit():
            # Buscar por CUIT (11 dígitos)
            print("DEBUG: Búsqueda por CUIT (11 dígitos)")
            cursor.execute('''
                SELECT id, tipoDocumento, nroDocumento, CUIT, apellido, nombres, 
                       fechaNacimiento, condicionIVA, categoriaMonotriibuto
                FROM clientes 
                WHERE REPLACE(REPLACE(CUIT, '-', ''), ' ', '') = ?
            ''', (busqueda,))
        elif busqueda.isdigit():
            # Buscar por DNI (menos de 11 dígitos)
            print("DEBUG: Búsqueda por DNI")
            cursor.execute('''
                SELECT id, tipoDocumento, nroDocumento, CUIT, apellido, nombres, 
                       fechaNacimiento, condicionIVA, categoriaMonotriibuto
                FROM clientes 
                WHERE nroDocumento = ?
            ''', (busqueda,))
        else:
            # Buscar por nombre (texto)
            print("DEBUG: Búsqueda por nombre")
            cursor.execute('''
                SELECT id, tipoDocumento, nroDocumento, CUIT, apellido, nombres, 
                       fechaNacimiento, condicionIVA, categoriaMonotriibuto
                FROM clientes 
                WHERE LOWER(apellido) LIKE LOWER(?) OR LOWER(nombres) LIKE LOWER(?)
            ''', (f'%{busqueda}%', f'%{busqueda}%'))
        
        # Obtener todos los resultados que coincidan
        clientes = cursor.fetchall()
        print(f"DEBUG: Encontrados {len(clientes)} clientes")
        
        if clientes:
            clientes_list = []
            for cliente in clientes:
                cliente_dict = {
                    'id': cliente[0],
                    'tipoDocumento': cliente[1],
                    'nroDocumento': cliente[2],
                    'cuit_dni': cliente[3],  # Usar cuit_dni para compatibilidad con frontend
                    'CUIT': cliente[3],
                    'apellido': cliente[4],
                    'nombres': cliente[5],
                    'nombre': f"{cliente[4]}, {cliente[5]}",  # Nombre completo para display
                    'fechaNacimiento': cliente[6],
                    'condicionIVA': cliente[7],
                    'categoriaMonotriibuto': cliente[8]
                }
                clientes_list.append(cliente_dict)
            
            conn.close()
            return jsonify({
                'clientes': clientes_list
            })
        else:
            conn.close()
            return jsonify({
                'clientes': [],  # Array vacío cuando no se encuentra
                'mensaje': 'Cliente no encontrado'
            })
    
    except Exception as e:
        print(f"Error en buscar_cliente: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor'
        }), 500

@app.route('/wsmtxca')
def wsmtxca():
    """Página de consulta WSMTXCA"""
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('consulta_wsmtxca.html')

@app.route('/consultar-wsmtxca')
def consultar_wsmtxca():
    """
    Endpoint para consultar comprobantes WSMTXCA (Factura Electrónica con Códigos MTX)
    
    Parámetros:
    - cuit: CUIT de la empresa (requerido)
    - tipo: Tipo de comprobante (requerido)
    - punto_venta: Punto de venta (requerido)
    - numero: Número del comprobante (requerido)
    """
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    # Validar parámetros
    cuit = request.args.get('cuit')
    tipo = request.args.get('tipo')
    punto_venta = request.args.get('punto_venta') 
    numero = request.args.get('numero')
    
    if not all([cuit, tipo, punto_venta, numero]):
        return jsonify({
            'success': False,
            'error': 'Parámetros faltantes',
            'detalle': 'Se requieren: cuit, tipo, punto_venta, numero'
        }), 400
    
    # Pre-chequeos
    modo_produccion = os.environ.get('INFOFISCAL_MODE') == 'production'
    if not modo_produccion:
        return jsonify({
            'success': False,
            'error': 'Aplicación no está en modo producción',
            'detalle': 'Configure INFOFISCAL_MODE=production'
        }), 400
    
    try:
        # Convertir parámetros
        tipo = int(tipo)
        punto_venta = int(punto_venta)
        numero = int(numero)
        
        # Importar cliente WSMTXCA
        import sys
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        
        from wsmtxca_client import crear_cliente_wsmtxca
        
        print(f"🔍 Consultando WSMTXCA - CUIT:{cuit} Tipo:{tipo} PV:{punto_venta} #{numero}")
        
        # Crear cliente y consultar
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        resultado = client.consultar_comprobante(
            cuit_representada=cuit,
            tipo_comprobante=tipo,
            punto_venta=punto_venta,
            numero_comprobante=numero
        )
        
        if resultado:
            # Exportar a archivo
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archivo = client.exportar_comprobante(resultado, 'json')
            
            # Preparar respuesta
            payload = {
                'success': True,
                'status': 'encontrado',
                'user_message': f'Comprobante encontrado exitosamente',
                'datos': {
                    'tipo_comprobante': resultado.get('tipo_comprobante'),
                    'punto_venta': resultado.get('punto_venta'),
                    'numero_comprobante': resultado.get('numero_comprobante'),
                    'fecha_emision': resultado.get('fecha_emision'),
                    'receptor_denominacion': resultado.get('receptor_denominacion'),
                    'receptor_numero_doc': resultado.get('receptor_numero_doc'),
                    'importe_total': resultado.get('importe_total'),
                    'importe_gravado': resultado.get('importe_gravado'),
                    'importe_iva': resultado.get('importe_iva'),
                    'cae': resultado.get('cae'),
                    'fecha_vencimiento_cae': resultado.get('fecha_vencimiento_cae'),
                    'cantidad_items': resultado.get('cantidad_items', 0)
                },
                'items': resultado.get('items', [])[:10],  # Primeros 10 items
                'archivo_exportado': archivo,
                'consulta': {
                    'cuit': cuit,
                    'tipo': tipo,
                    'punto_venta': punto_venta,
                    'numero': numero
                }
            }
            
            return jsonify(payload), 200
        else:
            # No encontrado
            return jsonify({
                'success': True,
                'status': 'no_encontrado',
                'user_message': 'El comprobante no existe en los registros de AFIP',
                'consulta': {
                    'cuit': cuit,
                    'tipo': tipo,
                    'punto_venta': punto_venta,
                    'numero': numero
                }
            }), 200
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Parámetros inválidos',
            'detalle': str(e)
        }), 400
    
    except Exception as e:
        print(f"❌ Error en consultar_wsmtxca: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Error consultando WSMTXCA',
            'detalle': str(e)
        }), 500

# ============= RUTAS WSFEv1 (FACTURAS TRADICIONALES) =============

@app.route('/wsfev1')
def wsfev1():
    """Página de consulta WSFEv1 (Facturas tradicionales desde 2013)"""
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Obtener cliente seleccionado desde la sesión (como WSMTXCA)
    cliente = session.get('cliente_seleccionado')
    
    return render_template('consulta_wsfev1.html', cliente=cliente)

@app.route('/buscar-facturas-wsfev1')
def buscar_facturas_wsfev1():
    """
    Endpoint para buscar todas las facturas WSFEv1 de una empresa
    
    Parámetros:
    - cuit: CUIT de la empresa (requerido)
    - limite: Límite de facturas por tipo (default: 50)
    """
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    cuit = request.args.get('cuit')
    limite = int(request.args.get('limite', 50))
    
    if not cuit:
        return jsonify({
            'success': False,
            'error': 'CUIT requerido'
        }), 400
    
    try:
        print(f"🔍 Iniciando búsqueda WSFEv1 para CUIT: {cuit}")
        
        # Importar el cliente WSFEv1
        import sys
        from pathlib import Path
        
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        
        from wsfev1_client import WSFEv1Client
        
        # Configurar rutas de certificados
        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'
        
        # Crear cliente WSFEv1
        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'  # Siempre usar producción
        )
        
        # Buscar comprobantes
        facturas = client.buscar_comprobantes_rango(
            cuit=cuit,
            tipos_comprobante=[1, 6, 11, 51, 2, 3, 7, 8, 12, 13],  # Tipos más comunes
            puntos_venta=[1, 2, 3, 4, 5],
            limite_por_tipo=limite
        )
        
        # Organizar resultados
        facturas_organizadas = {}
        total_facturas = len(facturas)
        
        for factura in facturas:
            tipo = factura['datos']['tipo_comprobante']
            if tipo not in facturas_organizadas:
                facturas_organizadas[tipo] = []
            facturas_organizadas[tipo].append(factura)
        
        if total_facturas > 0:
            return jsonify({
                'success': True,
                'total_facturas': total_facturas,
                'facturas_por_tipo': dict(sorted(facturas_organizadas.items())),
                'consulta': {
                    'cuit': cuit,
                    'limite_por_tipo': limite,
                    'servicio': 'WSFEv1'
                }
            }), 200
        else:
            return jsonify({
                'success': True,
                'total_facturas': 0,
                'mensaje': f'No se encontraron comprobantes para el CUIT {cuit}',
                'consulta': {
                    'cuit': cuit,
                    'limite_por_tipo': limite,
                    'servicio': 'WSFEv1'
                }
            }), 200
        
    except Exception as e:
        print(f"❌ Error en buscar_facturas_wsfev1: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': 'Error buscando facturas WSFEv1',
            'detalle': str(e)
        }), 500

@app.route('/consultar-wsfev1')
def consultar_wsfev1():
    """
    Endpoint para consultar una factura específica WSFEv1
    
    Parámetros:
    - cuit: CUIT de la empresa (requerido)
    - tipo: Tipo de comprobante (requerido)
    - punto_venta: Punto de venta (requerido)  
    - numero: Número del comprobante (requerido)
    """
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    cuit = request.args.get('cuit')
    tipo = request.args.get('tipo')
    punto_venta = request.args.get('punto_venta')
    numero = request.args.get('numero')
    
    if not all([cuit, tipo, punto_venta, numero]):
        return jsonify({
            'success': False,
            'error': 'Parámetros faltantes',
            'detalle': 'Se requieren: cuit, tipo, punto_venta, numero'
        }), 400
    
    try:
        # Importar el cliente WSFEv1
        import sys
        from pathlib import Path
        
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        
        from wsfev1_client import WSFEv1Client
        
        # Configurar rutas de certificados
        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'
        
        # Crear cliente WSFEv1
        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )
        
        # Consultar comprobante específico
        resultado = client.consultar_comprobante(
            cuit=cuit,
            tipo_comprobante=int(tipo),
            punto_venta=int(punto_venta),
            numero=int(numero)
        )
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f"❌ Error en consultar_wsfev1: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': 'Error consultando WSFEv1',
            'detalle': str(e)
        }), 500

# Endpoint para guardar cliente seleccionado en sesión
@app.route('/set-cliente-seleccionado', methods=['POST'])
def set_cliente_seleccionado():
    if 'usuario' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json()
    if not data:
        return '', 400
    session['cliente_seleccionado'] = data
    return '', 204

# Ruta para mostrar datos del cliente seleccionado en consultafacturacliente
@app.route('/consultafacturacliente')
def consulta_factura_cliente():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    cliente = session.get('cliente_seleccionado')
    if not cliente:
        return redirect(url_for('home'))
    return render_template('consultafacturacliente.html', cliente=cliente)

# Ruta para nuevo cliente
@app.route('/nuevo-cliente', methods=['GET', 'POST'])
def nuevo_cliente():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    mensaje = None
    error = None
    
    if request.method == 'POST':
        # Obtener datos del formulario
        tipoDocumento = request.form.get('tipoDocumento', '').strip()
        nroDocumento = request.form.get('nroDocumento', '').strip()
        CUIT = request.form.get('CUIT', '').strip()
        apellido = request.form.get('apellido', '').strip()
        nombres = request.form.get('nombres', '').strip()
        fechaNacimiento = request.form.get('fechaNacimiento', '').strip()
        condicionIVA = request.form.get('condicionIVA', '').strip()
        categoriaMonotriibuto = request.form.get('categoriaMonotriibuto', '').strip()
        
        # Función de validación de CUIT
        def validar_cuit(cuit_str):
            if not cuit_str:
                return True  # CUIT es opcional
            
            # Remover guiones y espacios
            cuit = cuit_str.replace('-', '').replace(' ', '')
            
            # Validar que sea numérico y tenga 11 dígitos
            if not cuit.isdigit() or len(cuit) != 11:
                return False
            
            # Validar dígito verificador
            multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
            suma = sum(int(cuit[i]) * multiplicadores[i] for i in range(10))
            resto = suma % 11
            dv = 11 - resto
            if dv == 11:
                dv = 0
            elif dv == 10:
                dv = 9
            
            return dv == int(cuit[10])
        
        # Validaciones del servidor
        errores = []
        
        # Validar tipo de documento
        if not tipoDocumento or tipoDocumento not in ['DNI', 'LE', 'LC']:
            errores.append('Debe seleccionar un tipo de documento válido')
        
        # Validar número de documento
        if not nroDocumento:
            errores.append('El número de documento es obligatorio')
        elif not nroDocumento.isdigit():
            errores.append('El número de documento debe ser numérico')
        elif len(nroDocumento) < 7 or len(nroDocumento) > 8:
            errores.append('El número de documento debe tener entre 7 y 8 dígitos')
        elif int(nroDocumento) < 1000000 or int(nroDocumento) > 99999999:
            errores.append('El número de documento debe estar entre 1.000.000 y 99.999.999')
        
        # Validar CUIT (opcional)
        if CUIT and not validar_cuit(CUIT):
            errores.append('El CUIT ingresado no es válido')
        
        # Validar apellido
        if not apellido:
            errores.append('El apellido es obligatorio')
        elif len(apellido) < 2:
            errores.append('El apellido debe tener al menos 2 caracteres')
        elif not all(c.isalpha() or c.isspace() or c in "áéíóúÁÉÍÓÚñÑüÜ'-" for c in apellido):
            errores.append('El apellido solo puede contener letras, espacios, acentos y guiones')
        
        # Validar nombres
        if not nombres:
            errores.append('Los nombres son obligatorios')
        elif len(nombres) < 2:
            errores.append('Los nombres deben tener al menos 2 caracteres')
        elif not all(c.isalpha() or c.isspace() or c in "áéíóúÁÉÍÓÚñÑüÜ'-" for c in nombres):
            errores.append('Los nombres solo pueden contener letras, espacios, acentos y guiones')
        
        # Validar monotributo
        if condicionIVA == 'Monotributo' and not categoriaMonotriibuto:
            errores.append('Debe seleccionar una categoría de monotributo')
        
        # Si hay errores, mostrarlos
        if errores:
            error = 'Se encontraron los siguientes errores:\n• ' + '\n• '.join(errores)
        else:
            try:
                # Verificar si ya existe el número de documento
                db_path = Path(__file__).parent.parent / 'infofiscal.db'
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT id FROM clientes WHERE nroDocumento = ? AND tipoDocumento = ?', 
                             (nroDocumento, tipoDocumento))
                if cursor.fetchone():
                    error = f'Ya existe un cliente con {tipoDocumento} {nroDocumento}'
                else:
                    # Formatear CUIT si existe
                    if CUIT:
                        cuit_clean = CUIT.replace('-', '').replace(' ', '')
                        CUIT = f"{cuit_clean[:2]}-{cuit_clean[2:10]}-{cuit_clean[10]}"
                    
                    # Capitalizar nombres
                    apellido = apellido.title()
                    nombres = nombres.title()
                    
                    # Insertar cliente
                    cursor.execute('''
                        INSERT INTO clientes (tipoDocumento, nroDocumento, CUIT, apellido, nombres, 
                                            fechaNacimiento, condicionIVA, categoriaMonotriibuto)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (tipoDocumento, nroDocumento, CUIT, apellido, nombres, 
                         fechaNacimiento, condicionIVA, categoriaMonotriibuto))
                    
                    conn.commit()
                    mensaje = f'Cliente {apellido}, {nombres} creado exitosamente con {tipoDocumento} {nroDocumento}'
                
            except Exception as e:
                error = f'Error al crear cliente: {str(e)}'
    
    return render_template('nuevo_cliente.html', usuario=session['usuario'], 
                         mensaje=mensaje, error=error)

# Ruta para consultar cliente por CUIT o DNI (AJAX)
@app.route('/consultar-cliente', methods=['GET'])
def consultar_cliente():
    if 'usuario' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    busqueda = request.args.get('busqueda', '').strip()
    if not busqueda:
        return jsonify({'error': 'Debe ingresar CUIT o DNI'}), 400
    db_path = Path(__file__).parent.parent / 'infofiscal.db'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT tipoDocumento, nroDocumento, CUIT, apellido, nombres, fechaNacimiento, condicionIVA, categoriaMonotriibuto FROM clientes WHERE CUIT = ? OR nroDocumento = ?''', (busqueda, busqueda))
    row = cursor.fetchone()
    if row:
        tipoDocumento, nroDocumento, CUIT, apellido, nombres, fechaNacimiento, condicionIVA, categoriaMonotriibuto = row
        return jsonify({
            'tipoDocumento': tipoDocumento,
            'nroDocumento': nroDocumento,
            'CUIT': CUIT,
            'apellido': apellido,
            'nombres': nombres,
            'fechaNacimiento': fechaNacimiento,
            'condicionIVA': condicionIVA,
            'categoriaMonotriibuto': categoriaMonotriibuto
        })
    else:
        return jsonify({'error': 'Cliente no encontrado'}), 404

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))


# Ruta de login
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']
        db_path = Path(__file__).parent.parent / 'infofiscal.db'
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT contrasena, bloqueado, cantidadDeIntentos FROM usuario WHERE usuario = ?', (usuario,))
        row = cursor.fetchone()
        if row:
            hashed, bloqueado, intentos = row
            if bloqueado:
                error = 'Usuario bloqueado.'
            elif get_bcrypt().checkpw(contrasena.encode('utf-8'), hashed):
                # Login exitoso: resetear intentos
                cursor.execute('UPDATE usuario SET cantidadDeIntentos = 0, fechaUltimoLogin = datetime("now") WHERE usuario = ?', (usuario,))
                conn.commit()
                session['usuario'] = usuario
                return redirect(url_for('home'))
            else:
                intentos = (intentos or 0) + 1
                if intentos >= 5:
                    cursor.execute('UPDATE usuario SET cantidadDeIntentos = ?, bloqueado = 1 WHERE usuario = ?', (intentos, usuario))
                    error = 'Usuario bloqueado por demasiados intentos fallidos.'
                else:
                    cursor.execute('UPDATE usuario SET cantidadDeIntentos = ? WHERE usuario = ?', (intentos, usuario))
                    error = f'Contraseña incorrecta. Intento {intentos} de 5.'
                conn.commit()
        else:
            error = 'Usuario no encontrado.'
    return render_template('login.html', error=error)


# Ruta principal protegida

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario = session['usuario']
    desbloqueado = None
    usuarios_bloqueados = []
    if usuario == 'admin':
        db_path = Path(__file__).parent.parent / 'infofiscal.db'
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == 'POST':
            user_to_unlock = request.form.get('user_to_unlock')
            if user_to_unlock:
                cursor.execute('UPDATE usuario SET bloqueado = 0, cantidadDeIntentos = 0 WHERE usuario = ?', (user_to_unlock,))
                conn.commit()
                desbloqueado = user_to_unlock
        cursor.execute('SELECT usuario FROM usuario WHERE bloqueado = 1')
        usuarios_bloqueados = [row[0] for row in cursor.fetchall()]
    return render_template('home.html', usuario=usuario, usuarios_bloqueados=usuarios_bloqueados, desbloqueado=desbloqueado)


# ============= RUTA UNIFICADA DE CONSULTA =============

@app.route('/consulta_facturas_unificada')
def consulta_facturas_unificada():
    """P�gina de consulta unificada de facturas"""
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('consulta_unificada.html')

@app.route('/consultar-facturas-unificada', methods=['GET', 'POST'])
def consultar_facturas_unificada():
    """
    Endpoint unificado que determina autom�ticamente qu� web service usar
    seg�n el tipo de cliente y ejecuta la consulta apropiada
    """
    if 'usuario' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    # Si es GET, mostrar página de consulta para el cliente seleccionado
    if request.method == 'GET':
        cliente_id = request.args.get('cliente_id')
        if not cliente_id:
            flash('No se especificó cliente', 'error')
            return redirect(url_for('consulta_facturas_unificada'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,))
            cliente = cursor.fetchone()
            conn.close()
            
            if not cliente:
                flash('Cliente no encontrado', 'error')
                return redirect(url_for('consulta_facturas_unificada'))
            
            # Convertir tupla a diccionario
            # Estructura: id, tipoDocumento, nroDocumento, CUIT, apellido, nombres, fechaNacimiento, condicionIVA, categoriaMonotriibuto
            cliente_dict = {
                'id': cliente[0],
                'cuit': cliente[3],  # CUIT está en posición 3
                'razon_social': f"{cliente[4]}, {cliente[5]}",  # apellido, nombres
                'condicion_iva': cliente[7] if len(cliente) > 7 else 'No especificado',  # condicionIVA
                'domicilio': '',  # No hay domicilio en esta tabla
                'tipo_documento': cliente[1],
                'nro_documento': cliente[2]
            }
            
            # EJECUTAR CONSULTA REAL DE FACTURAS  
            cuit = cliente_dict['cuit']
            print(f"DEBUG UNIFICADO: Iniciando consulta para cliente {cliente_dict['razon_social']} - CUIT: {cuit}")
            
            # Intentar TRES web services automáticamente usando las funciones adaptadas
            print("Consultando WSFEv1...")
            resultados_wsfev1 = consultar_wsfev1_interno(cuit)

            print("Consultando WSMTXCA...")
            resultados_wsmtxca = consultar_wsmtxca_interno(cuit)

            print("Consultando WSFEXv1...")
            resultados_wsfexv1 = consultar_wsfexv1_interno(cuit)

            # Determinar cuál tuvo éxito o más resultados
            facturas_wsfev1 = resultados_wsfev1.get('facturas', [])
            facturas_wsmtxca = resultados_wsmtxca.get('facturas', [])
            facturas_wsfexv1 = resultados_wsfexv1.get('facturas', [])

            total_wsfev1 = len(facturas_wsfev1)
            total_wsmtxca = len(facturas_wsmtxca)
            total_wsfexv1 = len(facturas_wsfexv1)

            # Combinar todas las facturas
            facturas_finales = facturas_wsfev1 + facturas_wsmtxca + facturas_wsfexv1

            # Determinar mensaje según los resultados
            servicios_con_datos = []
            if total_wsfev1 > 0:
                servicios_con_datos.append(f"WSFEv1 ({total_wsfev1})")
            if total_wsmtxca > 0:
                servicios_con_datos.append(f"WSMTXCA ({total_wsmtxca})")
            if total_wsfexv1 > 0:
                servicios_con_datos.append(f"WSFEXv1 ({total_wsfexv1})")

            if servicios_con_datos:
                web_service_usado = " + ".join(servicios_con_datos)
                mensaje = f"Se encontraron {len(facturas_finales)} facturas en total"
            else:
                web_service_usado = "Ninguno"
                facturas_finales = []
                mensaje = "No se encontraron facturas en ningún sistema"
            
            # Renderizar template con los resultados reales
            return render_template('resultado_facturas_unificada.html', 
                                 cliente=cliente_dict,
                                 facturas=facturas_finales,
                                 web_service=web_service_usado,
                                 mensaje=mensaje,
                                 total_facturas=len(facturas_finales))
            
        except Exception as e:
            print(f"ERROR en consultar_facturas_unificada: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('consulta_facturas_unificada'))
    
    # Si es POST, procesar la consulta de facturas
    try:
        cliente_id = request.form.get('cliente_id')
        cuit_cliente = request.form.get('cuit')
        
        if not cliente_id or not cuit_cliente:
            return jsonify({'error': 'Faltan datos del cliente'}), 400
        
        # Obtener informaci�n del cliente de la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,))
        cliente = cursor.fetchone()
        
        if not cliente:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        # Determinar qu� web service usar basado en el tipo de cliente
        # Aqu� implementamos la l�gica inteligente de selecci�n
        web_service = determinar_web_service(cliente, cuit_cliente)
        
        if web_service == 'WSFEV1':
            # Usar WSFEv1 para facturas tradicionales
            resultado = consultar_wsfev1_interno(cuit_cliente)
        elif web_service == 'WSMTXCA':
            # Usar WSMTXCA para c�digos MTX
            resultado = consultar_wsmtxca_interno(cuit_cliente)
        else:
            # Intentar ambos servicios
            resultado = consultar_ambos_servicios(cuit_cliente)
        
        return jsonify({
            'success': True,
            'web_service': resultado['web_service'],
            'total_facturas': len(resultado['facturas']),
            'facturas': resultado['facturas']
        })
        
    except Exception as e:
        return jsonify({'error': f'Error en consulta: {str(e)}'}), 500

def determinar_web_service(cliente, cuit):
    """
    L�gica inteligente para determinar qu� web service usar
    """
    try:
        # Primero intentamos con WSFEV1 (m�s com�n)
        # Si es un monotributista o empresa peque�a, probablemente use WSFEv1
        
        # Para simplificar, vamos a intentar primero WSFEv1
        # Si no hay resultados, intentamos WSMTXCA
        return 'AUTO'  # Modo autom�tico que prueba ambos
        
    except:
        return 'AUTO'

def consultar_wsfev1_interno(cuit):
    """Consultar facturas usando WSFEv1 - Adaptada de buscar_facturas_wsfev1"""
    try:
        print(f"DEBUG WSFEv1: Iniciando busqueda para CUIT: {cuit}")

        # Importar el cliente WSFEv1 (código adaptado de buscar_facturas_wsfev1)
        import sys
        from pathlib import Path

        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from wsfev1_client import WSFEv1Client

        # Configurar rutas de certificados
        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'

        print(f"DEBUG WSFEv1: Creando cliente con certificados...")

        # Crear cliente WSFEv1
        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'  # Siempre usar producción
        )

        # Buscar comprobantes (igual que la función original)
        print(f"DEBUG WSFEv1: Buscando comprobantes...")
        facturas = client.buscar_comprobantes_rango(
            cuit=cuit,
            tipos_comprobante=[1, 6, 11, 51, 2, 3, 7, 8, 12, 13],  # Tipos más comunes
            puntos_venta=[1, 2, 3, 4, 5],
            limite_por_tipo=10  # Reducido para el unificado
        )

        print(f"DEBUG WSFEv1: Encontradas {len(facturas) if facturas else 0} facturas")
        
        return {
            'web_service': 'WSFEv1 (Facturas Tradicionales)',
            'facturas': facturas or []
        }
    except Exception as e:
        print(f"DEBUG WSFEv1: ERROR - {str(e)}")
        return {
            'web_service': 'WSFEv1 (Error)',
            'facturas': [],
            'error': str(e)
        }

def consultar_wsmtxca_interno(cuit):
    """Consultar facturas usando WSMTXCA"""
    try:
        print(f"DEBUG WSMTXCA: Iniciando busqueda para CUIT: {cuit}")

        # Limpiar CUIT
        cuit_clean = cuit.replace('-', '').replace(' ', '')
        if not cuit_clean.isdigit() or len(cuit_clean) != 11:
            raise ValueError('CUIT debe tener 11 digitos numericos')

        # Importar cliente WSMTXCA (código adaptado de buscar_wsmtxca_completo)
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from wsmtxca_client import WSMTXCAClient

        # Configurar rutas de certificados
        cert_path = Path(__file__).parent.parent / 'certs' / 'certificado.crt'
        key_path = Path(__file__).parent.parent / 'certs' / 'clave_privada.key'

        print(f"DEBUG WSMTXCA: Creando cliente con certificados...")

        # Crear cliente WSMTXCA
        cliente = WSMTXCAClient(str(cert_path), str(key_path))

        # Búsqueda rápida (adaptado de la función original)
        tipos_principales = [11, 51, 1, 6]  # Factura C, M, A, B
        puntos_venta = [1, 2, 3, 4, 5]  # Puntos de venta más comunes

        facturas = []
        consultas_realizadas = 0
        max_consultas = 30

        print(f"DEBUG WSMTXCA: Consultando tipos {tipos_principales}")
        
        # Consultar rangos rápidos
        for tipo in tipos_principales:
            if consultas_realizadas >= max_consultas:
                break
            for pv in puntos_venta:
                if consultas_realizadas >= max_consultas:
                    break
                    
                no_encontrados = 0
                for num in range(1, 6):  # Solo primeros 5 números para rapidez
                    if consultas_realizadas >= max_consultas or no_encontrados >= 2:
                        break
                        
                    try:
                        consultas_realizadas += 1
                        resultado = cliente.consultar_comprobante(
                            cuit=cuit_clean,
                            tipo=tipo,
                            punto_venta=pv,
                            numero=num
                        )
                        
                        if resultado and resultado.get('status') == 'encontrado':
                            facturas.append(resultado)
                            no_encontrados = 0
                        else:
                            no_encontrados += 1
                            
                    except Exception:
                        no_encontrados += 1
        
        print(f"DEBUG WSMTXCA: Encontrados {len(facturas)} comprobantes")

        return {
            'web_service': 'WSMTXCA (Codigos MTX)',
            'facturas': facturas or []
        }
    except Exception as e:
        return {
            'web_service': 'WSMTXCA (Error)',
            'facturas': [],
            'error': str(e)
        }

def consultar_wsfexv1_interno(cuit):
    """Consultar facturas usando WSFEXv1 - Exportación"""
    try:
        print(f"DEBUG WSFEXv1: Iniciando busqueda para CUIT: {cuit}")

        # Importar el cliente WSFEXv1
        import sys
        from pathlib import Path

        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from wsfexv1_client import WSFEXv1Client

        # Configurar rutas de certificados
        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'

        print(f"DEBUG WSFEXv1: Creando cliente con certificados...")

        # Crear cliente WSFEXv1
        client = WSFEXv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )

        # Buscar comprobantes de exportación
        print(f"DEBUG WSFEXv1: Buscando comprobantes de exportación...")

        # Tipos comunes de exportación
        tipos_exportacion = [19, 20, 21]  # Facturas exportación A, B, C
        puntos_venta = [1, 2, 3, 4, 5]

        facturas = []

        # Intentar búsqueda básica (si el cliente lo soporta)
        # WSFEXv1 tiene métodos diferentes, adaptamos según disponibilidad
        try:
            # Método simplificado - consultar últimos comprobantes
            if hasattr(client, 'buscar_comprobantes_rango'):
                facturas = client.buscar_comprobantes_rango(
                    cuit=cuit,
                    tipos_comprobante=tipos_exportacion,
                    puntos_venta=puntos_venta,
                    limite_por_tipo=10
                )
        except Exception as inner_e:
            print(f"DEBUG WSFEXv1: No se pudo usar búsqueda avanzada: {str(inner_e)}")

        print(f"DEBUG WSFEXv1: Encontradas {len(facturas) if facturas else 0} facturas")

        return {
            'web_service': 'WSFEXv1 (Exportación)',
            'facturas': facturas or []
        }
    except Exception as e:
        print(f"DEBUG WSFEXv1: ERROR - {str(e)}")
        return {
            'web_service': 'WSFEXv1 (Error)',
            'facturas': [],
            'error': str(e)
        }

def consultar_ambos_servicios(cuit):
    """Consultar en ambos servicios y combinar resultados"""
    try:
        resultados_wsfev1 = consultar_wsfev1_interno(cuit)
        resultados_wsmtxca = consultar_wsmtxca_interno(cuit)
        resultados_wsfexv1 = consultar_wsfexv1_interno(cuit)
        
        facturas_combinadas = []
        
        # Agregar facturas de WSFEv1
        if resultados_wsfev1['facturas']:
            facturas_combinadas.extend(resultados_wsfev1['facturas'])

        # Agregar facturas de WSMTXCA
        if resultados_wsmtxca['facturas']:
            facturas_combinadas.extend(resultados_wsmtxca['facturas'])

        # Agregar facturas de WSFEXv1
        if resultados_wsfexv1['facturas']:
            facturas_combinadas.extend(resultados_wsfexv1['facturas'])
        
        # Determinar cu�l tuvo m�s �xito
        if len(resultados_wsfev1['facturas']) > len(resultados_wsmtxca['facturas']):
            servicio_principal = 'WSFEv1 (con respaldo WSMTXCA)'
        elif len(resultados_wsmtxca['facturas']) > 0:
            servicio_principal = 'WSMTXCA (con respaldo WSFEv1)'
        else:
            servicio_principal = 'Consulta autom�tica (ambos servicios)'
        
        return {
            'web_service': servicio_principal,
            'facturas': facturas_combinadas
        }
    except Exception as e:
        return {
            'web_service': 'Error en consulta autom�tica',
            'facturas': [],
            'error': str(e)
        }


if __name__ == '__main__':
    app.run(debug=True)



