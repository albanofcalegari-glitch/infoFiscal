# -*- coding: utf-8 -*-

# --- IMPORTS ---
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, flash, g
from pathlib import Path
import os
import requests as _requests

# Cargar variables de entorno del archivo .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

from flask_wtf.csrf import CSRFProtect

from src.config import Config
from src.db import init_pool, close_pool, health_check, get_cursor
from src.auth import auth_bp
from src.auth.decorators import login_required, role_required
from src.ssl_afip_config import crear_session_afip

# Configurar rutas absolutas para templates y static
template_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')

app = Flask(__name__,
           template_folder=template_folder,
           static_folder=static_folder)
app.secret_key = Config.SECRET_KEY

# Proteccion CSRF global — valida token en todo POST/PUT/DELETE
csrf = CSRFProtect(app)

# Registrar blueprint de autenticacion
app.register_blueprint(auth_bp)

# Inicializar pool PostgreSQL
init_pool()

import atexit
atexit.register(close_pool)



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
@login_required
@role_required('admin')
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

        # CUIT solicitante: dueño del certificado (estudio contable)
        consultor_cuit = Config.AFIP_SOLICITANTE_CUIT
        
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
@login_required
@role_required('admin', 'contador')
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
@login_required
@role_required('admin', 'contador')
def buscar_cliente():
    """Buscar cliente en la base de datos"""
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
        
        estudio_id = g.user['estudio_id']
        with get_cursor() as cur:
            if len(busqueda) == 11 and busqueda.isdigit():
                cur.execute("""
                    SELECT id, tipo_documento, nro_documento, cuit, apellido, nombres,
                           fecha_nacimiento, condicion_iva, categoria_monotributo
                    FROM clientes
                    WHERE estudio_id = %s
                      AND REPLACE(REPLACE(cuit, '-', ''), ' ', '') = %s
                """, (estudio_id, busqueda))
            elif busqueda.isdigit():
                cur.execute("""
                    SELECT id, tipo_documento, nro_documento, cuit, apellido, nombres,
                           fecha_nacimiento, condicion_iva, categoria_monotributo
                    FROM clientes
                    WHERE estudio_id = %s AND nro_documento = %s
                """, (estudio_id, busqueda))
            else:
                cur.execute("""
                    SELECT id, tipo_documento, nro_documento, cuit, apellido, nombres,
                           fecha_nacimiento, condicion_iva, categoria_monotributo
                    FROM clientes
                    WHERE estudio_id = %s
                      AND (LOWER(apellido) LIKE LOWER(%s) OR LOWER(nombres) LIKE LOWER(%s))
                """, (estudio_id, f'%{busqueda}%', f'%{busqueda}%'))

            clientes = cur.fetchall()

        if clientes:
            clientes_list = []
            for c in clientes:
                cliente_dict = {
                    'id': c['id'],
                    'tipoDocumento': c['tipo_documento'],
                    'nroDocumento': c['nro_documento'],
                    'cuit_dni': c['cuit'],
                    'CUIT': c['cuit'],
                    'apellido': c['apellido'],
                    'nombres': c['nombres'],
                    'nombre': f"{c['apellido']}, {c['nombres']}",
                    'fechaNacimiento': str(c['fecha_nacimiento']) if c['fecha_nacimiento'] else None,
                    'condicionIVA': c['condicion_iva'],
                    'categoriaMonotriibuto': c['categoria_monotributo']
                }
                clientes_list.append(cliente_dict)
            return jsonify({'clientes': clientes_list})
        else:
            return jsonify({
                'clientes': [],
                'mensaje': 'Cliente no encontrado'
            })
    
    except Exception as e:
        print(f"Error en buscar_cliente: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor'
        }), 500

@app.route('/wsmtxca')
@login_required
@role_required('admin', 'contador')
def wsmtxca():
    """Página de consulta WSMTXCA"""
    return render_template('consulta_wsmtxca.html')

@app.route('/consultar-wsmtxca')
@login_required
@role_required('admin', 'contador')
def consultar_wsmtxca():
    """
    Endpoint para consultar comprobantes WSMTXCA (Factura Electrónica con Códigos MTX)
    
    Parámetros:
    - cuit: CUIT de la empresa (requerido)
    - tipo: Tipo de comprobante (requerido)
    - punto_venta: Punto de venta (requerido)
    - numero: Número del comprobante (requerido)
    """
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
@login_required
@role_required('admin', 'contador')
def wsfev1():
    """Página de consulta WSFEv1 (Facturas tradicionales desde 2013)"""
    cliente = session.get('cliente_seleccionado')
    return render_template('consulta_wsfev1.html', cliente=cliente)

@app.route('/buscar-facturas-wsfev1')
@login_required
@role_required('admin', 'contador')
def buscar_facturas_wsfev1():
    """
    Endpoint para buscar todas las facturas WSFEv1 de una empresa

    Parámetros:
    - cuit: CUIT de la empresa (requerido)
    - limite: Límite de facturas por tipo (default: 50)
    """
    cuit = request.args.get('cuit')
    limite = int(request.args.get('limite', 50))
    
    if not cuit:
        return jsonify({
            'success': False,
            'error': 'CUIT requerido'
        }), 400
    
    try:
        print(f"[WSFEv1] solicitante={Config.AFIP_SOLICITANTE_CUIT}  cliente={cuit}")

        import sys
        from pathlib import Path

        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from wsfev1_client import WSFEv1Client

        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'

        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )

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
@login_required
@role_required('admin', 'contador')
def consultar_wsfev1():
    """
    Endpoint para consultar una factura específica WSFEv1
    
    Parámetros:
    - cuit: CUIT de la empresa (requerido)
    - tipo: Tipo de comprobante (requerido)
    - punto_venta: Punto de venta (requerido)  
    - numero: Número del comprobante (requerido)
    """
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
        print(f"[WSFEv1] solicitante={Config.AFIP_SOLICITANTE_CUIT}  cliente={cuit}  tipo={tipo}  pv={punto_venta}  nro={numero}")

        import sys
        from pathlib import Path

        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from wsfev1_client import WSFEv1Client

        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'

        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )

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
@login_required
@role_required('admin', 'contador')
def set_cliente_seleccionado():
    data = request.get_json()
    if not data:
        return '', 400
    session['cliente_seleccionado'] = data
    return '', 204

# Ruta para mostrar datos del cliente seleccionado en consultafacturacliente
@app.route('/consultafacturacliente')
@login_required
@role_required('admin', 'contador')
def consulta_factura_cliente():
    cliente = session.get('cliente_seleccionado')
    if not cliente:
        return redirect(url_for('home'))
    return render_template('consultafacturacliente.html', cliente=cliente)

# Ruta para nuevo cliente
@app.route('/nuevo-cliente', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'contador')
def nuevo_cliente():
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
                estudio_id = g.user['estudio_id']
                with get_cursor() as cur:
                    cur.execute(
                        'SELECT id FROM clientes WHERE estudio_id = %s AND nro_documento = %s AND tipo_documento = %s',
                        (estudio_id, nroDocumento, tipoDocumento)
                    )
                    if cur.fetchone():
                        error = f'Ya existe un cliente con {tipoDocumento} {nroDocumento}'
                    else:
                        # Formatear CUIT si existe
                        if CUIT:
                            cuit_clean = CUIT.replace('-', '').replace(' ', '')
                            CUIT = f"{cuit_clean[:2]}-{cuit_clean[2:10]}-{cuit_clean[10]}"

                        # Capitalizar nombres
                        apellido = apellido.title()
                        nombres = nombres.title()

                        cur.execute("""
                            INSERT INTO clientes (estudio_id, tipo_documento, nro_documento, cuit,
                                                  apellido, nombres, fecha_nacimiento,
                                                  condicion_iva, categoria_monotributo)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (estudio_id, tipoDocumento, nroDocumento, CUIT or None,
                              apellido, nombres, fechaNacimiento or None,
                              condicionIVA or None, categoriaMonotriibuto or None))

                        mensaje = f'Cliente {apellido}, {nombres} creado exitosamente con {tipoDocumento} {nroDocumento}'

            except Exception as e:
                error = f'Error al crear cliente: {str(e)}'
    
    return render_template('nuevo_cliente.html', usuario=g.user['nombre'],
                         mensaje=mensaje, error=error)

# Ruta para consultar cliente por CUIT o DNI (AJAX)
@app.route('/consultar-cliente', methods=['GET'])
@login_required
@role_required('admin', 'contador')
def consultar_cliente():
    busqueda = request.args.get('busqueda', '').strip()
    if not busqueda:
        return jsonify({'error': 'Debe ingresar CUIT o DNI'}), 400

    estudio_id = g.user['estudio_id']
    with get_cursor() as cur:
        cur.execute("""
            SELECT tipo_documento, nro_documento, cuit, apellido, nombres,
                   fecha_nacimiento, condicion_iva, categoria_monotributo
            FROM clientes
            WHERE estudio_id = %s AND (cuit = %s OR nro_documento = %s)
        """, (estudio_id, busqueda, busqueda))
        row = cur.fetchone()

    if row:
        return jsonify({
            'tipoDocumento': row['tipo_documento'],
            'nroDocumento': row['nro_documento'],
            'CUIT': row['cuit'],
            'apellido': row['apellido'],
            'nombres': row['nombres'],
            'fechaNacimiento': str(row['fecha_nacimiento']) if row['fecha_nacimiento'] else None,
            'condicionIVA': row['condicion_iva'],
            'categoriaMonotriibuto': row['categoria_monotributo']
        })
    else:
        return jsonify({'error': 'Cliente no encontrado'}), 404

# Ruta raiz redirige al login nuevo
@app.route('/')
def index():
    return redirect(url_for('auth.login_page'))

# Logout legacy redirige al logout nuevo
@app.route('/logout')
def logout():
    return redirect(url_for('auth.logout'))


# Ruta principal protegida

@app.route('/home', methods=['GET'])
@login_required
def home():
    # Superadmin va directo al dashboard de administración
    if g.user['rol'] == 'superadmin':
        return redirect(url_for('superadmin_dashboard'))
    return render_template('home.html',
                         usuario=g.user['nombre'],
                         rol=g.user['rol'],
                         usuarios_bloqueados=[],
                         desbloqueado=None)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG AFIP — certificados y credenciales por estudio (solo admin)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/config/afip', methods=['GET'])
@login_required
@role_required('admin', 'contador', 'superadmin')
def config_afip():
    """Ver configuraciones AFIP del estudio del usuario logueado."""
    estudio_id = g.user['estudio_id']
    if estudio_id is None:
        flash('Superadmin no tiene estudio asignado.', 'error')
        return redirect(url_for('home'))

    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM estudios_afip
            WHERE estudio_id = %s
            ORDER BY activo DESC, id DESC
        """, (estudio_id,))
        configs = cur.fetchall()

    return render_template('config_afip.html', configs=configs)


@app.route('/config/afip/upload', methods=['POST'])
@login_required
@role_required('admin', 'contador', 'superadmin')
def config_afip_upload():
    """Subir certificado y clave AFIP."""
    from src.afip_credentials import encrypt_portal_password

    estudio_id = g.user['estudio_id']
    if estudio_id is None:
        flash('Superadmin no tiene estudio asignado.', 'error')
        return redirect(url_for('home'))

    solicitante_cuit = request.form.get('solicitante_cuit', '').strip()
    ambiente = request.form.get('ambiente', 'prod')
    portal_cuit = request.form.get('portal_cuit', '').strip() or None
    portal_password = request.form.get('portal_password', '').strip()

    cert_file = request.files.get('cert_file')
    key_file = request.files.get('key_file')

    if not solicitante_cuit:
        flash('El CUIT solicitante es obligatorio.', 'error')
        return redirect(url_for('config_afip'))

    if not cert_file or not cert_file.filename:
        flash('Debe seleccionar el archivo de certificado.', 'error')
        return redirect(url_for('config_afip'))

    if not key_file or not key_file.filename:
        flash('Debe seleccionar el archivo de clave privada.', 'error')
        return redirect(url_for('config_afip'))

    # Leer archivos como bytes
    cert_blob = cert_file.read()
    key_blob = key_file.read()

    # Validacion basica: verificar que parecen certificados
    cert_text = cert_blob.decode('utf-8', errors='ignore')
    if 'CERTIFICATE' not in cert_text and 'BEGIN' not in cert_text:
        flash('El archivo de certificado no parece valido.', 'error')
        return redirect(url_for('config_afip'))

    key_text = key_blob.decode('utf-8', errors='ignore')
    if 'KEY' not in key_text and 'BEGIN' not in key_text:
        flash('El archivo de clave privada no parece valido.', 'error')
        return redirect(url_for('config_afip'))

    # Encriptar password del portal si se proporcionó
    portal_password_enc = None
    if portal_password:
        portal_password_enc = encrypt_portal_password(portal_password)

    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO estudios_afip
                    (estudio_id, solicitante_cuit, cert_blob, key_blob,
                     ambiente, portal_cuit, portal_password_enc, activo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
            """, (estudio_id, solicitante_cuit, cert_blob, key_blob,
                  ambiente, portal_cuit, portal_password_enc))

        flash('Configuracion AFIP guardada correctamente.', 'success')
    except Exception as e:
        flash(f'Error al guardar: {e}', 'error')

    return redirect(url_for('config_afip'))


@app.route('/config/afip/<int:config_id>/toggle', methods=['POST'])
@login_required
@role_required('admin', 'contador', 'superadmin')
def config_afip_toggle(config_id):
    """Activar/desactivar una configuracion AFIP."""
    estudio_id = g.user['estudio_id']
    with get_cursor() as cur:
        cur.execute(
            "SELECT activo FROM estudios_afip WHERE id = %s AND estudio_id = %s",
            (config_id, estudio_id))
        cfg = cur.fetchone()
        if not cfg:
            flash('Configuracion no encontrada.', 'error')
            return redirect(url_for('config_afip'))

        cur.execute(
            "UPDATE estudios_afip SET activo = %s WHERE id = %s AND estudio_id = %s",
            (not cfg['activo'], config_id, estudio_id))

    flash('Estado actualizado.', 'success')
    return redirect(url_for('config_afip'))


@app.route('/config/afip/<int:config_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'contador', 'superadmin')
def config_afip_delete(config_id):
    """Eliminar una configuracion AFIP."""
    estudio_id = g.user['estudio_id']
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM estudios_afip WHERE id = %s AND estudio_id = %s",
            (config_id, estudio_id))
        if cur.rowcount == 0:
            flash('Configuracion no encontrada.', 'error')
        else:
            flash('Configuracion eliminada.', 'success')

    return redirect(url_for('config_afip'))


# ══════════════════════════════════════════════════════════════════════════════
# SUPERADMIN — gestión de estudios y membresías
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/admin', methods=['GET'])
@app.route('/admin/dashboard', methods=['GET'])
@login_required
@role_required('superadmin')
def superadmin_dashboard():
    """Dashboard con KPIs generales del sistema."""
    from datetime import date, timedelta
    hoy = date.today()
    limite_vencimiento = hoy + timedelta(days=15)

    with get_cursor() as cur:
        # KPIs
        cur.execute("SELECT COUNT(*) AS total FROM estudios")
        total = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) AS c FROM estudios WHERE activo = TRUE")
        activos = cur.fetchone()['c']

        cur.execute("""
            SELECT COUNT(*) AS c FROM estudios
            WHERE membresia_hasta IS NOT NULL AND membresia_hasta < %s
        """, (hoy,))
        vencidos = cur.fetchone()['c']

        cur.execute("SELECT COUNT(*) AS c FROM usuarios WHERE activo = TRUE AND rol != 'superadmin'")
        total_usuarios = cur.fetchone()['c']

        cur.execute("""
            SELECT COUNT(*) AS c FROM consultas_log
            WHERE created_at >= DATE_TRUNC('month', NOW())
        """)
        consultas_mes = cur.fetchone()['c']

        # Distribucion por plan
        cur.execute("""
            SELECT COALESCE(plan, 'trial') AS plan, COUNT(*) AS cantidad
            FROM estudios GROUP BY plan ORDER BY cantidad DESC
        """)
        planes = cur.fetchall()

        # Ultimos 5 estudios
        cur.execute("SELECT * FROM estudios ORDER BY created_at DESC LIMIT 5")
        recientes = cur.fetchall()

        # Membresias por vencer en 15 dias (o ya vencidas)
        cur.execute("""
            SELECT * FROM estudios
            WHERE membresia_hasta IS NOT NULL
              AND membresia_hasta <= %s
              AND activo = TRUE
            ORDER BY membresia_hasta ASC
        """, (limite_vencimiento,))
        por_vencer = cur.fetchall()

    kpis = {
        'total': total,
        'activos': activos,
        'vencidos': vencidos,
        'total_usuarios': total_usuarios,
        'consultas_mes': consultas_mes,
    }

    return render_template('superadmin_dashboard.html',
                         kpis=kpis,
                         planes=planes,
                         recientes=recientes,
                         por_vencer=por_vencer,
                         hoy=hoy,
                         active_page='dashboard')


@app.route('/admin/estudios', methods=['GET'])
@login_required
@role_required('superadmin')
def superadmin_panel():
    """Panel principal: listar todos los estudios con estado de membresía."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT e.*,
                   COUNT(DISTINCT u.id) AS total_usuarios,
                   COUNT(DISTINCT c.id) AS total_clientes,
                   (SELECT COUNT(*) FROM consultas_log cl
                    WHERE cl.estudio_id = e.id
                      AND cl.created_at >= DATE_TRUNC('month', NOW())) AS consultas_este_mes
            FROM estudios e
            LEFT JOIN usuarios u ON u.estudio_id = e.id AND u.activo = TRUE
            LEFT JOIN clientes c ON c.estudio_id = e.id
            GROUP BY e.id
            ORDER BY e.created_at DESC
        """)
        estudios = cur.fetchall()

    from datetime import date
    hoy = date.today()

    return render_template('superadmin_estudios.html',
                         estudios=estudios,
                         hoy=hoy,
                         active_page='estudios')


@app.route('/admin/estudios/<int:estudio_id>/toggle', methods=['POST'])
@login_required
@role_required('superadmin')
def superadmin_toggle_estudio(estudio_id):
    """Activar/desactivar un estudio (membresía)."""
    with get_cursor() as cur:
        cur.execute("SELECT activo FROM estudios WHERE id = %s", (estudio_id,))
        estudio = cur.fetchone()
        if not estudio:
            flash('Estudio no encontrado', 'error')
            return redirect(url_for('superadmin_panel'))

        nuevo_estado = not estudio['activo']
        cur.execute("""
            UPDATE estudios SET activo = %s, updated_at = NOW() WHERE id = %s
        """, (nuevo_estado, estudio_id))

    estado_txt = 'activado' if nuevo_estado else 'desactivado'
    flash(f'Estudio {estado_txt} correctamente', 'success')
    return redirect(url_for('superadmin_panel'))


@app.route('/admin/estudios/<int:estudio_id>/plan', methods=['POST'])
@login_required
@role_required('superadmin')
def superadmin_update_plan(estudio_id):
    """Actualizar plan y vencimiento de membresía."""
    plan = request.form.get('plan')
    membresia_hasta = request.form.get('membresia_hasta')
    max_clientes = request.form.get('max_clientes', type=int)
    max_usuarios = request.form.get('max_usuarios', type=int)
    max_consultas = request.form.get('max_consultas_mes', type=int)
    notas = request.form.get('notas_admin', '')

    with get_cursor() as cur:
        cur.execute("""
            UPDATE estudios
            SET plan = %s,
                membresia_hasta = %s,
                max_clientes = COALESCE(%s, max_clientes),
                max_usuarios = COALESCE(%s, max_usuarios),
                max_consultas_mes = COALESCE(%s, max_consultas_mes),
                notas_admin = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (plan, membresia_hasta or None, max_clientes, max_usuarios,
              max_consultas, notas, estudio_id))

    flash('Plan actualizado', 'success')
    return redirect(url_for('superadmin_detalle_estudio', estudio_id=estudio_id))


@app.route('/admin/estudios/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('superadmin')
def superadmin_crear_estudio():
    """Formulario para crear un estudio nuevo con su usuario admin."""
    if request.method == 'GET':
        return render_template('superadmin_crear_estudio.html',
                             active_page='crear_estudio')

    # POST — crear estudio + usuario admin
    from src.auth.service import hash_password

    nombre = request.form.get('nombre', '').strip()
    email = request.form.get('email', '').strip()
    cuit = request.form.get('cuit', '').strip() or None
    telefono = request.form.get('telefono', '').strip() or None
    domicilio = request.form.get('domicilio', '').strip() or None
    plan = request.form.get('plan', 'trial')
    membresia_hasta = request.form.get('membresia_hasta') or None
    max_clientes = request.form.get('max_clientes', 10, type=int)
    max_usuarios = request.form.get('max_usuarios', 2, type=int)
    max_consultas = request.form.get('max_consultas_mes', 100, type=int)
    notas = request.form.get('notas_admin', '').strip()

    admin_nombre = request.form.get('admin_nombre', '').strip()
    admin_email = request.form.get('admin_email', '').strip()
    admin_password = request.form.get('admin_password', '')

    if not nombre or not email or not admin_nombre or not admin_email or not admin_password:
        flash('Todos los campos obligatorios deben completarse.', 'error')
        return redirect(url_for('superadmin_crear_estudio'))

    if len(admin_password) < 8:
        flash('La contrasena debe tener al menos 8 caracteres.', 'error')
        return redirect(url_for('superadmin_crear_estudio'))

    try:
        with get_cursor() as cur:
            # Verificar email de estudio duplicado
            cur.execute("SELECT id FROM estudios WHERE email = %s", (email,))
            if cur.fetchone():
                flash('Ya existe un estudio con ese email.', 'error')
                return redirect(url_for('superadmin_crear_estudio'))

            # Verificar email de usuario duplicado
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (admin_email,))
            if cur.fetchone():
                flash('Ya existe un usuario con ese email.', 'error')
                return redirect(url_for('superadmin_crear_estudio'))

            # Crear estudio
            cur.execute("""
                INSERT INTO estudios (nombre, email, cuit, telefono, domicilio,
                                     plan, membresia_hasta, max_clientes,
                                     max_usuarios, max_consultas_mes, notas_admin)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (nombre, email, cuit, telefono, domicilio, plan,
                  membresia_hasta, max_clientes, max_usuarios, max_consultas, notas))
            estudio_id = cur.fetchone()['id']

            # Crear usuario admin del estudio
            password_hash = hash_password(admin_password)
            cur.execute("""
                INSERT INTO usuarios (estudio_id, nombre, email, password_hash, rol)
                VALUES (%s, %s, %s, %s, 'admin')
            """, (estudio_id, admin_nombre, admin_email, password_hash))

        flash(f'Estudio "{nombre}" creado correctamente con usuario admin.', 'success')
        return redirect(url_for('superadmin_detalle_estudio', estudio_id=estudio_id))

    except Exception as e:
        flash(f'Error al crear estudio: {e}', 'error')
        return redirect(url_for('superadmin_crear_estudio'))


@app.route('/admin/health', methods=['GET'])
@login_required
@role_required('superadmin')
def superadmin_health():
    """Estado de servicios AFIP y sesiones del sistema."""
    estado_afip = _afip_health_check()

    with get_cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS c FROM sesiones
            WHERE revocada = FALSE AND expires_at > NOW()
        """)
        sesiones_activas = cur.fetchone()['c']

        cur.execute("""
            SELECT COUNT(*) AS c FROM sesiones
            WHERE revocada = TRUE OR expires_at <= NOW()
        """)
        sesiones_expiradas = cur.fetchone()['c']

    return render_template('superadmin_health.html',
                         estado_afip=estado_afip,
                         sesiones_activas=sesiones_activas,
                         sesiones_expiradas=sesiones_expiradas,
                         active_page='health')


@app.route('/admin/cleanup-sessions', methods=['POST'])
@login_required
@role_required('superadmin')
def superadmin_cleanup_sessions():
    """Limpiar sesiones expiradas/revocadas."""
    from src.auth.service import cleanup_expired_sessions
    eliminadas = cleanup_expired_sessions()
    flash(f'{eliminadas} sesiones eliminadas.', 'success')
    return redirect(url_for('superadmin_health'))


@app.route('/admin/estudios/<int:estudio_id>', methods=['GET'])
@login_required
@role_required('superadmin')
def superadmin_detalle_estudio(estudio_id):
    """Detalle de un estudio: usuarios, clientes, config AFIP, logs."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM estudios WHERE id = %s", (estudio_id,))
        estudio = cur.fetchone()
        if not estudio:
            flash('Estudio no encontrado', 'error')
            return redirect(url_for('superadmin_panel'))

        cur.execute("""
            SELECT id, nombre, email, rol, activo, ultimo_login, created_at
            FROM usuarios WHERE estudio_id = %s ORDER BY created_at
        """, (estudio_id,))
        usuarios = cur.fetchall()

        cur.execute("SELECT COUNT(*) AS total FROM clientes WHERE estudio_id = %s", (estudio_id,))
        total_clientes = cur.fetchone()['total']

        cur.execute("""
            SELECT * FROM estudios_afip
            WHERE estudio_id = %s ORDER BY activo DESC, id DESC
        """, (estudio_id,))
        configs_afip = cur.fetchall()

        cur.execute("""
            SELECT servicio, COUNT(*) AS total, SUM(cantidad) AS comprobantes,
                   MAX(created_at) AS ultima
            FROM consultas_log
            WHERE estudio_id = %s AND created_at >= DATE_TRUNC('month', NOW())
            GROUP BY servicio
        """, (estudio_id,))
        uso_mes = cur.fetchall()

    return render_template('superadmin_detalle_estudio.html',
                         estudio=estudio,
                         usuarios=usuarios,
                         total_clientes=total_clientes,
                         configs_afip=configs_afip,
                         uso_mes=uso_mes,
                         active_page='estudios')


# ============= HEALTH CHECK AFIP =============

_AFIP_ENDPOINTS = {
    'WSFEv1':  'https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL',
    'WSMTXCA': 'https://serviciosjava.afip.gov.ar/wsmtxca/services/MTXCAService?wsdl',
    'WSFEXv1': 'https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL',
}

def _afip_health_check(timeout=4):
    """Ping rapido a los WSDL de AFIP. Retorna dict {servicio: bool}."""
    s = crear_session_afip()
    estado = {}
    for nombre, url in _AFIP_ENDPOINTS.items():
        try:
            r = s.get(url, timeout=timeout)
            estado[nombre] = r.status_code == 200
        except Exception:
            estado[nombre] = False
    s.close()
    return estado


# ============= RUTA UNIFICADA DE CONSULTA =============

@app.route('/consulta_facturas_unificada')
@login_required
@role_required('admin', 'contador')
def consulta_facturas_unificada():
    """Pagina de consulta unificada de facturas"""
    return render_template('consulta_unificada.html')

@app.route('/consultar-facturas-unificada', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'contador')
def consultar_facturas_unificada():
    """
    Endpoint unificado que determina automaticamente que web service usar
    segun el tipo de cliente y ejecuta la consulta apropiada
    """
    
    # Si es GET, mostrar página de consulta para el cliente seleccionado
    if request.method == 'GET':
        cliente_id = request.args.get('cliente_id')
        if not cliente_id:
            flash('No se especificó cliente', 'error')
            return redirect(url_for('consulta_facturas_unificada'))
        
        try:
            estudio_id = g.user['estudio_id']
            with get_cursor() as cur:
                cur.execute('SELECT * FROM clientes WHERE estudio_id = %s AND id = %s',
                            (estudio_id, cliente_id))
                cliente = cur.fetchone()

            if not cliente:
                flash('Cliente no encontrado', 'error')
                return redirect(url_for('consulta_facturas_unificada'))

            cliente_dict = {
                'id': cliente['id'],
                'cuit': cliente['cuit'],
                'razon_social': f"{cliente['apellido']}, {cliente['nombres']}",
                'condicion_iva': cliente['condicion_iva'] or 'No especificado',
                'domicilio': '',
                'tipo_documento': cliente['tipo_documento'],
                'nro_documento': cliente['nro_documento']
            }
            
            # EJECUTAR CONSULTA REAL DE FACTURAS
            # cuit_cliente = CUIT del emisor consultado (sale de la DB)
            # solicitante  = CUIT del estudio que posee el certificado (sale de Config)
            cuit = cliente_dict['cuit']
            fecha_desde = request.args.get('fecha_desde', '')  # formato YYYY-MM-DD
            fecha_hasta = request.args.get('fecha_hasta', '')
            # Convertir a YYYYMMDD que usa AFIP, validar formato
            fecha_desde_afip = fecha_desde.replace('-', '') if fecha_desde else None
            fecha_hasta_afip = fecha_hasta.replace('-', '') if fecha_hasta else None
            # Validar que las fechas tengan 8 dígitos y empiecen con 19xx o 20xx
            for f in [fecha_desde_afip, fecha_hasta_afip]:
                if f and (len(f) != 8 or not f.isdigit() or f[:2] not in ('19', '20')):
                    flash(f'Fecha invalida: {f}. Use formato DD/MM/AAAA con año completo.', 'error')
                    return redirect(url_for('consulta_facturas_unificada'))
            print(f"[UNIFICADO] solicitante={Config.AFIP_SOLICITANTE_CUIT}  cliente={cuit}  razon_social={cliente_dict['razon_social']}  fecha_desde={fecha_desde_afip}  fecha_hasta={fecha_hasta_afip}")

            # Pre-check: verificar que al menos un servicio AFIP responda
            estado_afip = _afip_health_check(timeout=4)
            print(f"[HEALTH CHECK] {estado_afip}")

            if not any(estado_afip.values()):
                caidos = ', '.join(estado_afip.keys())
                return render_template('resultado_facturas_unificada.html',
                    cliente=cliente_dict,
                    facturas=[],
                    web_service='Ninguno',
                    mensaje=f'Los servicios de AFIP no estan disponibles en este momento ({caidos}). Intente nuevamente mas tarde.',
                    total_facturas=0,
                    afip_caido=True)

            # Mensaje informativo segun filtro de fechas
            modo_consulta = ''
            if fecha_desde_afip and fecha_hasta_afip:
                modo_consulta = f'Rango: {fecha_desde_afip[:4]}-{fecha_desde_afip[4:6]}-{fecha_desde_afip[6:]} a {fecha_hasta_afip[:4]}-{fecha_hasta_afip[4:6]}-{fecha_hasta_afip[6:]}'
            else:
                modo_consulta = 'Sin fechas: se muestran los ultimos 50 comprobantes por tipo/PV'

            # WSFEv1 es el servicio principal — cubre todos los tipos (A,B,C,M)
            # Cada servicio en su propio try/except para que uno no tire abajo a los demas
            resultados_wsfev1 = {'facturas': []}
            resultados_wsmtxca = {'facturas': []}
            resultados_wsfexv1 = {'facturas': []}
            errores_servicios = []

            if estado_afip.get('WSFEv1'):
                try:
                    resultados_wsfev1 = consultar_wsfev1_interno(cuit, fecha_desde_afip, fecha_hasta_afip, estudio_id=g.user['estudio_id'])
                except Exception as e:
                    print(f"[UNIFICADO] WSFEv1 fallo: {e}", flush=True)
                    errores_servicios.append(f"WSFEv1: {e}")

            # WSMTXCA y WSFEXv1 solo si WSFEv1 falló completamente (error, no "0 resultados")
            # WSFEv1 ya cubre Facturas A/B/C/M para mercado interno.
            # WSMTXCA es lento (~30 llamadas SOAP) y redundante para monotributo.
            # WSFEXv1 solo aplica a exportadores.
            # Para PVs no-WS (Factura en Linea, Factuweb) el usuario tiene RCEL.
            wsfev1_fallo = resultados_wsfev1.get('error') and not resultados_wsfev1.get('facturas')
            if wsfev1_fallo:
                print(f"[UNIFICADO] WSFEv1 fallo, intentando WSMTXCA/WSFEXv1...", flush=True)
                if estado_afip.get('WSMTXCA'):
                    try:
                        resultados_wsmtxca = consultar_wsmtxca_interno(cuit, fecha_desde_afip, fecha_hasta_afip)
                    except Exception as e:
                        print(f"[UNIFICADO] WSMTXCA fallo: {e}", flush=True)
                        errores_servicios.append(f"WSMTXCA: {e}")

                if estado_afip.get('WSFEXv1'):
                    try:
                        resultados_wsfexv1 = consultar_wsfexv1_interno(cuit, fecha_desde_afip, fecha_hasta_afip)
                    except Exception as e:
                        print(f"[UNIFICADO] WSFEXv1 fallo: {e}", flush=True)
                        errores_servicios.append(f"WSFEXv1: {e}")
            else:
                print(f"[UNIFICADO] WSFEv1 OK, saltando WSMTXCA/WSFEXv1", flush=True)

            # Combinar resultados WS
            facturas_ws = (
                resultados_wsfev1.get('facturas', []) +
                resultados_wsmtxca.get('facturas', []) +
                resultados_wsfexv1.get('facturas', [])
            )
            print(f"[UNIFICADO] WS: {len(facturas_ws)} comprobantes", flush=True)

            # ── RCEL (portal web) — emitidos + recibidos ──
            facturas_rcel = []
            facturas_recibidas = []
            from src.afip_credentials import get_afip_credentials
            _creds = get_afip_credentials(g.user['estudio_id'])
            portal_cuit = _creds['portal_cuit']
            portal_pass = _creds['portal_password']
            cuit_clean = str(cuit).replace('-', '').replace(' ', '')

            if portal_cuit and portal_pass:
                import sys as _sys
                _root = Path(__file__).parent.parent
                if str(_root) not in _sys.path:
                    _sys.path.insert(0, str(_root))
                from rcel_scraper import RCELScraper

                # Fechas YYYYMMDD -> dd/mm/yyyy
                rcel_desde = '01/01/2020'
                rcel_hasta = None
                if fecha_desde_afip and len(fecha_desde_afip) == 8:
                    rcel_desde = f"{fecha_desde_afip[6:]}/{fecha_desde_afip[4:6]}/{fecha_desde_afip[:4]}"
                if fecha_hasta_afip and len(fecha_hasta_afip) == 8:
                    rcel_hasta = f"{fecha_hasta_afip[6:]}/{fecha_hasta_afip[4:6]}/{fecha_hasta_afip[:4]}"

                portal_cuit_clean = portal_cuit.replace('-', '').replace(' ', '')
                if cuit_clean == portal_cuit_clean:
                    empresa_nombre = None
                    empresa_cuit = None
                else:
                    empresa_nombre = cliente_dict['razon_social']
                    empresa_cuit = cuit_clean

                rcel_kwargs = dict(puntos_venta=None, fecha_desde=rcel_desde,
                                   fecha_hasta=rcel_hasta, empresa=empresa_nombre,
                                   cuit_empresa=empresa_cuit)

                # ── RCEL emitidos ──
                try:
                    print(f"[UNIFICADO] RCEL emitidos para {cuit_clean}...", flush=True)
                    scraper = RCELScraper(cuit=portal_cuit, password=portal_pass, headless=True)
                    res = scraper.consultar(**rcel_kwargs, seccion='emitidos')
                    if res.get('comprobantes'):
                        facturas_rcel = RCELScraper.normalizar_comprobantes(res['comprobantes'], 'emitidos')
                        print(f"[UNIFICADO] RCEL emitidos: {len(facturas_rcel)}", flush=True)
                    elif res.get('error'):
                        print(f"[UNIFICADO] RCEL emitidos error: {res['error']}", flush=True)
                        errores_servicios.append(f"RCEL emitidos: {res['error']}")
                except Exception as e:
                    print(f"[UNIFICADO] RCEL emitidos fallo: {e}", flush=True)
                    errores_servicios.append(f"RCEL emitidos: {e}")

                # ── RCEL recibidos ──
                try:
                    print(f"[UNIFICADO] RCEL recibidos para {cuit_clean}...", flush=True)
                    scraper2 = RCELScraper(cuit=portal_cuit, password=portal_pass, headless=True)
                    res2 = scraper2.consultar(**rcel_kwargs, seccion='recibidos')
                    if res2.get('comprobantes'):
                        facturas_recibidas = RCELScraper.normalizar_comprobantes(res2['comprobantes'], 'recibidos')
                        print(f"[UNIFICADO] RCEL recibidos: {len(facturas_recibidas)}", flush=True)
                    elif res2.get('error'):
                        print(f"[UNIFICADO] RCEL recibidos error: {res2['error']}", flush=True)
                        errores_servicios.append(f"RCEL recibidos: {res2['error']}")
                except Exception as e:
                    print(f"[UNIFICADO] RCEL recibidos fallo: {e}", flush=True)
                    errores_servicios.append(f"RCEL recibidos: {e}")
            else:
                print(f"[UNIFICADO] RCEL: credenciales portal no configuradas", flush=True)

            # ── Unificar emitidos ──
            facturas_finales = facturas_ws + facturas_rcel

            if facturas_finales or facturas_recibidas:
                partes = []
                if facturas_finales:
                    partes.append(f"{len(facturas_finales)} emitidos")
                if facturas_recibidas:
                    partes.append(f"{len(facturas_recibidas)} recibidos")
                mensaje = f"Se encontraron {' + '.join(partes)}. {modo_consulta}"
                web_service_usado = f"{len(facturas_ws)} via WS + {len(facturas_rcel)} via Portal"
            else:
                web_service_usado = "Ninguno"
                if errores_servicios:
                    mensaje = f"Error en consulta: {'; '.join(errores_servicios)}"
                else:
                    mensaje = f"No se encontraron comprobantes. {modo_consulta}"

            # Persistir resultados en disco — siempre 3 archivos: emitidos, recibidos, todos
            _eid = g.user['estudio_id']
            _gf_kwargs = dict(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, estudio_id=_eid)
            archivos_guardados = {
                'emitidos':  _guardar_facturas(cuit, facturas_finales, web_service_usado, sufijo='emitidos', **_gf_kwargs),
                'recibidos': _guardar_facturas(cuit, facturas_recibidas, 'RCEL recibidos', sufijo='recibidos', **_gf_kwargs),
                'todos':     _guardar_facturas(cuit, facturas_finales + facturas_recibidas, web_service_usado, sufijo='todos', **_gf_kwargs),
            }

            # ── Resumen agrupado por tipo de comprobante ──
            # Notas de Crédito (tipos 3/8/13/53) restan del total — se acumulan con signo negativo
            _NC_CODIGOS = {'3', '8', '13', '53'}

            def _es_nota_credito(d, c):
                tipo_num = str(d.get('CbteTipo', '') or c.get('tipo', '') or '').strip()
                if tipo_num in _NC_CODIGOS:
                    return True
                desc = str(c.get('tipo_descripcion', '') or d.get('CbteTipoDesc', '') or '').lower()
                return 'crédito' in desc or 'credito' in desc

            resumen_por_tipo = {}
            resumen_impositivo = {'neto': 0.0, 'iva': 0.0, 'tributos': 0.0, 'exento': 0.0, 'total': 0.0,
                                  'iva_por_alicuota': {}, 'tributos_por_tipo': {}}

            for fac in facturas_finales:
                d = fac.get('datos', fac) if isinstance(fac, dict) else fac
                c = fac.get('consulta', {}) if isinstance(fac, dict) else {}
                tipo = c.get('tipo_descripcion', '') or d.get('CbteTipoDesc', d.get('CbteTipo', d.get('tipo_comprobante', 'Otro')))
                tipo = str(tipo)

                def _float(val):
                    try:
                        return float(val or 0)
                    except (ValueError, TypeError):
                        return 0.0

                signo = -1 if _es_nota_credito(d, c) else 1

                imp_total = _float(d.get('ImpTotal', d.get('importe_total', 0))) * signo
                imp_neto = _float(d.get('ImpNeto', 0)) * signo
                imp_iva = _float(d.get('ImpIVA', 0)) * signo
                imp_trib = _float(d.get('ImpTrib', 0)) * signo
                imp_opex = _float(d.get('ImpOpEx', 0)) * signo

                if tipo not in resumen_por_tipo:
                    resumen_por_tipo[tipo] = {'cantidad': 0, 'importe': 0.0}
                resumen_por_tipo[tipo]['cantidad'] += 1
                resumen_por_tipo[tipo]['importe'] += imp_total

                # Acumular totales impositivos
                resumen_impositivo['neto'] += imp_neto
                resumen_impositivo['iva'] += imp_iva
                resumen_impositivo['tributos'] += imp_trib
                resumen_impositivo['exento'] += imp_opex
                resumen_impositivo['total'] += imp_total

                # Desglose IVA por alícuota (solo disponible en WSFEv1)
                for alic in d.get('IvaDetalle', []):
                    alic_id = alic.get('Id', '?')
                    alic_imp = _float(alic.get('Importe', 0)) * signo
                    alic_base = _float(alic.get('BaseImp', 0)) * signo
                    if alic_id not in resumen_impositivo['iva_por_alicuota']:
                        resumen_impositivo['iva_por_alicuota'][alic_id] = {'base': 0.0, 'importe': 0.0}
                    resumen_impositivo['iva_por_alicuota'][alic_id]['base'] += alic_base
                    resumen_impositivo['iva_por_alicuota'][alic_id]['importe'] += alic_imp

                # Desglose tributos por tipo (IIBB, municipal, etc.)
                for trib in d.get('TributosDetalle', []):
                    trib_desc = trib.get('Desc', f"Tributo {trib.get('Id', '?')}")
                    trib_imp = _float(trib.get('Importe', 0)) * signo
                    trib_base = _float(trib.get('BaseImp', 0)) * signo
                    if trib_desc not in resumen_impositivo['tributos_por_tipo']:
                        resumen_impositivo['tributos_por_tipo'][trib_desc] = {'base': 0.0, 'importe': 0.0}
                    resumen_impositivo['tributos_por_tipo'][trib_desc]['base'] += trib_base
                    resumen_impositivo['tributos_por_tipo'][trib_desc]['importe'] += trib_imp

            resumen_ordenado = sorted(resumen_por_tipo.items(), key=lambda x: x[1]['cantidad'], reverse=True)

            # Mapeo de alícuotas IVA AFIP
            IVA_ALICUOTAS = {'3': '0%', '4': '10.5%', '5': '21%', '6': '27%', '8': '5%', '9': '2.5%'}
            iva_detalle = []
            for alic_id, datos in sorted(resumen_impositivo['iva_por_alicuota'].items()):
                iva_detalle.append({
                    'alicuota': IVA_ALICUOTAS.get(str(alic_id), f'{alic_id}%'),
                    'base': datos['base'],
                    'importe': datos['importe'],
                })

            tributos_detalle = []
            for desc, datos in sorted(resumen_impositivo['tributos_por_tipo'].items()):
                tributos_detalle.append({
                    'descripcion': desc,
                    'base': datos['base'],
                    'importe': datos['importe'],
                })

            # Determinar si mostrar sección impositiva (solo si hay IVA o tributos > 0)
            tiene_impuestos = resumen_impositivo['iva'] > 0 or resumen_impositivo['tributos'] > 0

            # Marcar origen en cada comprobante para la grilla unificada
            for fac in facturas_finales:
                fac['_origen'] = 'Emitido'
            for fac in facturas_recibidas:
                fac['_origen'] = 'Recibido'
            todos_comprobantes = facturas_finales + facturas_recibidas

            return render_template('resultado_facturas_unificada.html',
                                 cliente=cliente_dict,
                                 todos_comprobantes=todos_comprobantes,
                                 web_service=web_service_usado,
                                 mensaje=mensaje,
                                 total_facturas=len(facturas_finales),
                                 total_recibidas=len(facturas_recibidas),
                                 archivos=archivos_guardados,
                                 fecha_desde=fecha_desde,
                                 fecha_hasta=fecha_hasta,
                                 resumen_por_tipo=resumen_ordenado,
                                 resumen_impositivo=resumen_impositivo,
                                 iva_detalle=iva_detalle,
                                 tributos_detalle=tributos_detalle,
                                 tiene_impuestos=tiene_impuestos)
            
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
        
        # Obtener informacion del cliente de la base de datos
        estudio_id = g.user['estudio_id']
        with get_cursor() as cur:
            cur.execute('SELECT * FROM clientes WHERE estudio_id = %s AND id = %s',
                        (estudio_id, cliente_id))
            cliente = cur.fetchone()

        if not cliente:
            return jsonify({'error': 'Cliente no encontrado'}), 404

        # Determinar que web service usar basado en el tipo de cliente
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

        try:
            _guardar_facturas(cuit_cliente, resultado['facturas'], resultado['web_service'])
        except Exception:
            pass

        return jsonify({
            'success': True,
            'web_service': resultado['web_service'],
            'total_facturas': len(resultado['facturas']),
            'facturas': resultado['facturas']
        })
        
    except Exception as e:
        return jsonify({'error': f'Error en consulta: {str(e)}'}), 500

def _guardar_facturas(cuit_cliente, facturas, web_service, sufijo=None, fecha_desde=None, fecha_hasta=None, estudio_id=None):
    """Guardar resultados de consulta AFIP en JSON y CSV.

    Siempre genera archivos, incluso si facturas está vacía (genera archivos vacíos).

    Args:
        sufijo: 'emitidos', 'recibidos', 'todos' — se agrega al nombre del archivo.
        fecha_desde: fecha inicio consulta (YYYYMMDD o YYYY-MM-DD) para nomenclatura.
        fecha_hasta: fecha fin consulta para nomenclatura.
        estudio_id: scoping multi-tenant — archivos van a facturas/{estudio_id}/{cuit}/
    """
    try:
        from datetime import datetime
        import json
        import csv

        root_dir = Path(__file__).parent.parent
        if estudio_id:
            out_dir = root_dir / 'facturas' / str(estudio_id) / cuit_cliente
        else:
            out_dir = root_dir / 'facturas' / cuit_cliente
        out_dir.mkdir(parents=True, exist_ok=True)

        # Nomenclatura: facturas_{cuit}_{fechaDesde}_a_{fechaHasta}_{sufijo}
        fd = (fecha_desde or '').replace('-', '')
        fh = (fecha_hasta or '').replace('-', '')
        rango = f"_{fd}_a_{fh}" if fd and fh else f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        tag = f"_{sufijo}" if sufijo else ""
        base = f"facturas_{cuit_cliente}{rango}{tag}"

        # ── Normalizar cada factura a dict plano ─────────────────────
        columnas = ['origen', 'tipo', 'tipo_codigo', 'punto_venta', 'numero',
                     'fecha', 'importe_total', 'importe_neto', 'importe_iva',
                     'cae', 'cae_vto', 'doc_nro', 'moneda']

        filas = []
        for f in (facturas or []):
            d = f.get('datos', f) if isinstance(f, dict) else f
            c = f.get('consulta', {}) if isinstance(f, dict) else {}
            filas.append({
                'origen':         f.get('_origen', 'Emitido'),
                'tipo':           c.get('tipo_descripcion', '') or d.get('CbteTipo', d.get('tipo_comprobante', '')),
                'tipo_codigo':    c.get('tipo', d.get('CbteTipo', d.get('tipo_comprobante', ''))),
                'punto_venta':    d.get('PtoVta', d.get('punto_venta', '')),
                'numero':         d.get('CbteNro', d.get('numero_comprobante', d.get('numero', ''))),
                'fecha':          d.get('CbteFch', d.get('fecha_emision', '')),
                'importe_total':  d.get('ImpTotal', d.get('importe_total', '')),
                'importe_neto':   d.get('ImpNeto', d.get('importe_gravado', '')),
                'importe_iva':    d.get('ImpIVA', d.get('importe_iva', '')),
                'cae':            d.get('CAE', d.get('cae', '')),
                'cae_vto':        d.get('CAEFchVto', d.get('fecha_vencimiento_cae', d.get('fecha_vto_cae', ''))),
                'doc_nro':        d.get('DocNro', d.get('receptor_nro_doc', d.get('receptor_numero_doc', ''))),
                'moneda':         d.get('MonId', d.get('moneda', '')),
            })

        # ── JSON ─────────────────────────────────────────────────────
        json_path = out_dir / f"{base}.json"
        payload = {
            'cuit_cliente': cuit_cliente,
            'solicitante': Config.AFIP_SOLICITANTE_CUIT,
            'fecha_consulta': datetime.now().isoformat(),
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'web_service': web_service,
            'tipo': sufijo or 'emitidos',
            'total': len(filas),
            'comprobantes': filas,
        }
        with open(json_path, 'w', encoding='utf-8') as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)

        # ── CSV (compatible Excel: sep=; y BOM UTF-8) ────────────────
        csv_path = out_dir / f"{base}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as fp:
            writer = csv.DictWriter(fp, fieldnames=columnas, delimiter=';')
            writer.writeheader()
            writer.writerows(filas)

        print(f"[GUARDAR] {len(filas)} facturas -> {json_path.name}, {csv_path.name}")
        return {'json': str(json_path), 'csv': str(csv_path)}

    except Exception as e:
        print(f"[GUARDAR] ERROR: {e}")
        return None


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

def consultar_wsfev1_interno(cuit_cliente, fecha_desde=None, fecha_hasta=None, estudio_id=None):
    """Consultar facturas usando WSFEv1 — patron eficiente basado en script.

    1. Obtiene PVs reales via FEParamGetPtosVenta (1 sola llamada SOAP)
    2. Solo recorre tipos principales
    3. Early stop por fecha
    """
    import sys, time
    from pathlib import Path
    from src.afip_credentials import get_afip_credentials

    creds = get_afip_credentials(estudio_id)
    solicitante = creds['solicitante_cuit']
    cuit_clean = str(cuit_cliente).replace('-', '').replace(' ', '')
    print(f"[WSFEv1] solicitante={solicitante}  cliente={cuit_clean}  desde={fecha_desde}  hasta={fecha_hasta}", flush=True)

    try:
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from wsfev1_client import WSFEv1Client

        client = WSFEv1Client(creds['cert_path'], creds['key_path'], creds['ambiente'])

        # Obtener PVs reales (1 sola llamada SOAP — evita recorrer PVs inexistentes)
        pvs_reales = client.obtener_puntos_venta(cuit_clean)
        if not pvs_reales:
            pvs_reales = [1, 2, 3, 4, 5]
        print(f"[WSFEv1] PVs detectados: {pvs_reales}", flush=True)

        tipos = [1, 6, 11, 51, 2, 3, 7, 8, 12, 13]
        facturas = []
        inicio = time.time()

        for tipo in tipos:
            for pv in pvs_reales:
                ultimo = client.obtener_ultimo_comprobante(cuit_clean, tipo, pv)
                if not ultimo or ultimo <= 0:
                    continue

                print(f"[WSFEv1] tipo={tipo} pv={pv} ultimo={ultimo}", flush=True)

                # Con fechas: búsqueda binaria para encontrar el rango exacto
                if fecha_desde and fecha_hasta:
                    rango = client.buscar_rango_por_fecha(cuit_clean, tipo, pv, ultimo, fecha_desde, fecha_hasta)
                    if not rango:
                        print(f"[WSFEv1] tipo={tipo} pv={pv} sin comprobantes en rango {fecha_desde}-{fecha_hasta}", flush=True)
                        continue
                    num_inicio, num_fin = rango
                    print(f"[WSFEv1] tipo={tipo} pv={pv} rango encontrado: #{num_inicio}-#{num_fin} ({num_fin - num_inicio + 1} comprobantes)", flush=True)
                else:
                    num_fin = ultimo
                    num_inicio = max(1, ultimo - 49)

                for num in range(num_fin, num_inicio - 1, -1):
                    try:
                        comp = client.consultar_comprobante(cuit_clean, tipo, pv, num)
                        if comp is None:
                            continue

                        # Safety net: validar fecha dentro del rango solicitado
                        fecha_cbte = comp.get('CbteFch') or comp.get('fecha_emision') or ''
                        if fecha_desde and fecha_cbte and fecha_cbte < fecha_desde:
                            continue
                        if fecha_hasta and fecha_cbte and fecha_cbte > fecha_hasta:
                            continue

                        comp['CUIT'] = cuit_clean
                        comp['PtoVta'] = str(pv)
                        comp['CbteTipo'] = str(tipo)
                        comp['CbteTipoDesc'] = client.tipos_comprobante.get(tipo, f'Tipo {tipo}')
                        comp['CbteNro'] = str(num)
                        comp['consulta'] = {
                            'cuit': cuit_clean,
                            'tipo': tipo,
                            'tipo_descripcion': client.tipos_comprobante.get(tipo, f'Tipo {tipo}'),
                            'punto_venta': pv,
                            'numero': num,
                            'numero_formateado': f"{pv:04d}-{num:08d}"
                        }
                        facturas.append(comp)
                    except Exception:
                        continue

        elapsed = time.time() - inicio
        print(f"[WSFEv1] cliente={cuit_clean}  encontradas={len(facturas)}  tiempo={elapsed:.1f}s", flush=True)

        return {
            'web_service': 'WSFEv1 (Facturas Tradicionales)',
            'facturas': facturas
        }
    except Exception as e:
        print(f"[WSFEv1] ERROR cliente={cuit_clean}: {e}", flush=True)
        return {
            'web_service': 'WSFEv1 (Error)',
            'facturas': [],
            'error': str(e)
        }

def consultar_wsmtxca_interno(cuit_cliente, fecha_desde=None, fecha_hasta=None):
    """Consultar facturas usando WSMTXCA.

    Args:
        cuit_cliente: CUIT del emisor consultado (el cliente del estudio).
        fecha_desde: str YYYYMMDD o None
        fecha_hasta: str YYYYMMDD o None
    """
    solicitante = Config.AFIP_SOLICITANTE_CUIT
    print(f"[WSMTXCA] solicitante={solicitante}  cliente={cuit_cliente}")

    try:
        cuit_clean = cuit_cliente.replace('-', '').replace(' ', '')
        if not cuit_clean.isdigit() or len(cuit_clean) != 11:
            raise ValueError('CUIT debe tener 11 digitos numericos')

        import sys
        from pathlib import Path
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from wsmtxca_client import WSMTXCAClient

        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'

        cliente = WSMTXCAClient(str(cert_path), str(key_path))

        tipos_principales = [11, 51, 1, 6]
        puntos_venta = [1, 2, 3, 4, 5]

        facturas = []
        consultas_realizadas = 0
        max_consultas = 30

        for tipo in tipos_principales:
            if consultas_realizadas >= max_consultas:
                break
            for pv in puntos_venta:
                if consultas_realizadas >= max_consultas:
                    break

                no_encontrados = 0
                for num in range(1, 6):
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
                            fecha_cbte = resultado.get('CbteFch') or resultado.get('fecha_emision') or ''
                            if fecha_hasta and fecha_cbte > fecha_hasta:
                                no_encontrados += 1
                                continue
                            if fecha_desde and fecha_cbte < fecha_desde:
                                break
                            facturas.append(resultado)
                            no_encontrados = 0
                        else:
                            no_encontrados += 1

                    except Exception:
                        no_encontrados += 1

        print(f"[WSMTXCA] cliente={cuit_clean}  encontrados={len(facturas)}")

        return {
            'web_service': 'WSMTXCA (Codigos MTX)',
            'facturas': facturas or []
        }
    except Exception as e:
        print(f"[WSMTXCA] ERROR cliente={cuit_cliente}: {e}")
        return {
            'web_service': 'WSMTXCA (Error)',
            'facturas': [],
            'error': str(e)
        }

def consultar_wsfexv1_interno(cuit_cliente, fecha_desde=None, fecha_hasta=None):
    """Consultar facturas usando WSFEXv1 - Exportación.

    Args:
        cuit_cliente: CUIT del emisor consultado (el cliente del estudio).
        fecha_desde: str YYYYMMDD o None
        fecha_hasta: str YYYYMMDD o None
    """
    solicitante = Config.AFIP_SOLICITANTE_CUIT
    print(f"[WSFEXv1] solicitante={solicitante}  cliente={cuit_cliente}")

    try:
        import sys
        from pathlib import Path

        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from wsfexv1_client import WSFEXv1Client

        cert_path = root_dir / 'certs' / 'certificado.crt'
        key_path = root_dir / 'certs' / 'clave_privada.key'

        client = WSFEXv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )

        # Tipos comunes de exportación
        tipos_exportacion = [19, 20, 21]  # Facturas exportación A, B, C
        puntos_venta = [1, 2, 3, 4, 5]

        facturas = []

        try:
            if hasattr(client, 'buscar_comprobantes_rango'):
                facturas = client.buscar_comprobantes_rango(
                    cuit=cuit_cliente,
                    tipos_comprobante=tipos_exportacion,
                    puntos_venta=puntos_venta,
                    limite_por_tipo=10,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta
                )
        except Exception as inner_e:
            print(f"[WSFEXv1] busqueda fallida cliente={cuit_cliente}: {inner_e}")

        print(f"[WSFEXv1] cliente={cuit_cliente}  encontradas={len(facturas) if facturas else 0}")

        return {
            'web_service': 'WSFEXv1 (Exportación)',
            'facturas': facturas or []
        }
    except Exception as e:
        print(f"[WSFEXv1] ERROR cliente={cuit_cliente}: {e}")
        return {
            'web_service': 'WSFEXv1 (Error)',
            'facturas': [],
            'error': str(e)
        }

def consultar_ambos_servicios(cuit_cliente):
    """Consultar en los 3 servicios y combinar resultados."""
    try:
        resultados_wsfev1 = consultar_wsfev1_interno(cuit_cliente)
        resultados_wsmtxca = consultar_wsmtxca_interno(cuit_cliente)
        resultados_wsfexv1 = consultar_wsfexv1_interno(cuit_cliente)
        
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


# ═══════════════════════════════════════════════════════════════════
# RCEL Scraping — Comprobantes via portal web (PVs no cubiertos por WS)
# ═══════════════════════════════════════════════════════════════════

@app.route('/consultar-rcel')
@login_required
def consultar_rcel():
    """Consultar comprobantes via scraping RCEL (PVs Factura en Linea / Factuweb)."""
    cliente_id = request.args.get('cliente_id')
    cuit = request.args.get('cuit', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')

    # Obtener datos del cliente de la DB
    cliente = None
    if cliente_id:
        try:
            with get_cursor() as cur:
                cur.execute("SELECT * FROM clientes WHERE id = %s", (cliente_id,))
                row = cur.fetchone()
                if row:
                    cols = [d[0] for d in cur.description]
                    cliente = dict(zip(cols, row))
        except Exception:
            pass

    if not cliente:
        cliente = {'id': cliente_id, 'cuit': cuit, 'razon_social': '', 'condicion_iva': ''}

    # Verificar credenciales del portal
    portal_cuit = Config.AFIP_PORTAL_CUIT
    portal_pass = Config.AFIP_PORTAL_PASSWORD
    if not portal_cuit or not portal_pass:
        return render_template('resultado_rcel.html',
            cliente=cliente, facturas=[], total_facturas=0,
            error='Credenciales del portal AFIP no configuradas (AFIP_PORTAL_CUIT / AFIP_PORTAL_PASSWORD en .env)')

    # Convertir fechas dd/mm/yyyy para RCEL
    rcel_desde = '01/01/2020'
    rcel_hasta = None  # default = hoy
    if fecha_desde:
        try:
            parts = fecha_desde.split('-')
            rcel_desde = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass
    if fecha_hasta:
        try:
            parts = fecha_hasta.split('-')
            rcel_hasta = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass

    print(f"[RCEL ROUTE] cliente={cuit} desde={rcel_desde} hasta={rcel_hasta}", flush=True)

    try:
        import sys
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from rcel_scraper import RCELScraper

        scraper = RCELScraper(cuit=portal_cuit, password=portal_pass, headless=True)
        resultado = scraper.consultar(
            puntos_venta=None,  # todos los disponibles
            fecha_desde=rcel_desde,
            fecha_hasta=rcel_hasta,
        )

        if resultado.get('error'):
            return render_template('resultado_rcel.html',
                cliente=cliente, facturas=[], total_facturas=0,
                error=resultado['error'])

        # Normalizar al formato del sistema
        facturas = RCELScraper.normalizar_comprobantes(resultado['comprobantes'])

        # Guardar archivos
        if facturas:
            cuit_guardar = (cuit or '').replace('-', '').replace(' ', '') or portal_cuit
            _guardar_facturas(cuit_guardar, facturas, 'RCEL (Portal Web)')

        return render_template('resultado_rcel.html',
            cliente=cliente,
            facturas=facturas,
            total_facturas=len(facturas),
            empresa=resultado.get('empresa', ''),
            pvs_consultados=resultado.get('pvs_consultados', []),
            pvs_disponibles=resultado.get('pvs_disponibles', []),
            tiempo=resultado.get('tiempo'),
            error=None)

    except Exception as e:
        print(f"[RCEL ROUTE] ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return render_template('resultado_rcel.html',
            cliente=cliente, facturas=[], total_facturas=0,
            error=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# LIQUIDACIÓN IVA — posición mensual y Libro IVA Digital
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/iva')
@login_required
@role_required('admin', 'contador')
def liquidacion_iva():
    """Dashboard de liquidación de IVA mensual."""
    from src.liquidacion_iva import calcular_posicion_iva
    from decimal import Decimal
    from datetime import date

    periodo = request.args.get('periodo', date.today().strftime('%Y-%m'))
    saldo_anterior = Decimal(request.args.get('saldo_anterior', '0'))
    estudio_id = g.user['estudio_id']

    posicion = None
    try:
        with get_cursor() as cur:
            posicion = calcular_posicion_iva(cur, estudio_id, periodo,
                                             saldo_anterior=saldo_anterior)
    except Exception as e:
        flash(f'Error calculando IVA: {e}', 'error')

    pos_dict = None
    if posicion:
        pos_dict = {
            'periodo': posicion.periodo,
            'ventas_gravadas': float(posicion.ventas_gravadas),
            'ventas_iva_105': float(posicion.ventas_iva_105),
            'ventas_iva_21': float(posicion.ventas_iva_21),
            'ventas_iva_27': float(posicion.ventas_iva_27),
            'ventas_exentas': float(posicion.ventas_exentas),
            'ventas_no_gravadas': float(posicion.ventas_no_gravadas),
            'total_debito': float(posicion.total_debito),
            'cant_ventas': posicion.cant_ventas,
            'compras_gravadas': float(posicion.compras_gravadas),
            'compras_iva_105': float(posicion.compras_iva_105),
            'compras_iva_21': float(posicion.compras_iva_21),
            'compras_iva_27': float(posicion.compras_iva_27),
            'compras_exentas': float(posicion.compras_exentas),
            'compras_no_gravadas': float(posicion.compras_no_gravadas),
            'total_credito': float(posicion.total_credito),
            'cant_compras': posicion.cant_compras,
            'saldo_tecnico': float(posicion.saldo_tecnico),
            'saldo_anterior': float(posicion.saldo_anterior),
            'resultado': float(posicion.resultado),
        }

    return render_template('liquidacion_iva.html',
                         posicion=pos_dict, periodo=periodo,
                         saldo_anterior=float(saldo_anterior))


@app.route('/iva/libro')
@login_required
@role_required('admin', 'contador')
def libro_iva_digital():
    """Libro IVA Digital — detalle de comprobantes del período."""
    from src.liquidacion_iva import generar_libro_iva_digital
    from datetime import date

    periodo = request.args.get('periodo', date.today().strftime('%Y-%m'))
    estudio_id = g.user['estudio_id']

    with get_cursor() as cur:
        libro = generar_libro_iva_digital(cur, estudio_id, periodo)

    return render_template('libro_iva.html', libro=libro, periodo=periodo)


# ══════════════════════════════════════════════════════════════════════════════
# EMISIÓN DE FACTURAS — solicitud de CAE via WSFEv1
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/emitir-factura', methods=['GET'])
@login_required
@role_required('admin', 'contador')
def emitir_factura():
    """Formulario de emisión de factura electrónica."""
    estudio_id = g.user['estudio_id']

    with get_cursor() as cur:
        cur.execute("""
            SELECT ce.*, ea.solicitante_cuit
            FROM comprobantes_emitidos ce
            JOIN estudios_afip ea ON ea.estudio_id = ce.estudio_id AND ea.activo = TRUE
            WHERE ce.estudio_id = %s
            ORDER BY ce.created_at DESC LIMIT 10
        """, (estudio_id,))
        ultimos = cur.fetchall()

    from src.emision_factura import TIPOS_COMPROBANTE
    for u in ultimos:
        u['tipo_desc'] = TIPOS_COMPROBANTE.get(u['tipo_comprobante'], '')

    return render_template('emitir_factura.html', resultado=None, ultimos=ultimos)


@app.route('/emitir-factura', methods=['POST'])
@login_required
@role_required('admin', 'contador')
def emitir_factura_post():
    """Procesar emisión de factura y solicitar CAE."""
    from src.emision_factura import DatosFactura, ItemFactura, solicitar_cae, TIPOS_COMPROBANTE
    from decimal import Decimal
    from datetime import date, datetime
    import json

    estudio_id = g.user['estudio_id']

    # Obtener credenciales AFIP del estudio
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM estudios_afip
            WHERE estudio_id = %s AND activo = TRUE AND ambiente = 'prod'
            LIMIT 1
        """, (estudio_id,))
        afip_config = cur.fetchone()

    if not afip_config:
        flash('No hay configuración AFIP activa. Configure certificados primero.', 'error')
        return redirect(url_for('emitir_factura'))

    # Parsear items
    item_count = int(request.form.get('item_count', 0))
    items = []
    for i in range(item_count):
        desc = request.form.get(f'item_desc_{i}', '').strip()
        if not desc:
            continue
        items.append(ItemFactura(
            descripcion=desc,
            cantidad=Decimal(request.form.get(f'item_cant_{i}', '1')),
            precio_unitario=Decimal(request.form.get(f'item_precio_{i}', '0')),
            alicuota_iva_id=int(request.form.get(f'item_iva_{i}', '5')),
        ))

    if not items:
        flash('Debe agregar al menos un item.', 'error')
        return redirect(url_for('emitir_factura'))

    # Parsear fechas
    def parse_date(name):
        val = request.form.get(name, '').strip()
        if val:
            return datetime.strptime(val, '%Y-%m-%d').date()
        return None

    datos = DatosFactura(
        tipo_comprobante=int(request.form.get('tipo_comprobante', 11)),
        punto_venta=int(request.form.get('punto_venta', 1)),
        concepto=int(request.form.get('concepto', 2)),
        tipo_doc_receptor=int(request.form.get('tipo_doc_receptor', 80)),
        nro_doc_receptor=request.form.get('nro_doc_receptor', '').replace('-', '').replace(' ', ''),
        receptor_nombre=request.form.get('receptor_nombre', '').strip(),
        items=items,
        fecha_serv_desde=parse_date('fecha_serv_desde'),
        fecha_serv_hasta=parse_date('fecha_serv_hasta'),
        fecha_vto_pago=parse_date('fecha_vto_pago'),
    )

    # Crear cliente WSFEv1 con credenciales del estudio
    import tempfile
    cert_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.crt')
    key_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.key')

    try:
        cert_tmp.write(afip_config['cert_blob'])
        cert_tmp.close()
        key_tmp.write(afip_config['key_blob'])
        key_tmp.close()

        import sys
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        from wsfev1_client import WSFEv1Client

        client = WSFEv1Client(cert_tmp.name, key_tmp.name, ambiente='prod')
        resultado = solicitar_cae(client, afip_config['solicitante_cuit'], datos)

        # Guardar en DB
        items_json = json.dumps([
            {'desc': it.descripcion, 'cant': float(it.cantidad),
             'precio': float(it.precio_unitario), 'iva_id': it.alicuota_iva_id}
            for it in items
        ])

        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO comprobantes_emitidos
                    (estudio_id, cuit_emisor, cuit_receptor, receptor_nombre,
                     tipo_doc_receptor, nro_doc_receptor,
                     tipo_comprobante, punto_venta, numero_desde, numero_hasta,
                     fecha_emision, importe_total, importe_neto, importe_iva,
                     concepto, fecha_serv_desde, fecha_serv_hasta, fecha_vto_pago,
                     cae, cae_vto, estado, observaciones, items_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                estudio_id, afip_config['solicitante_cuit'],
                datos.nro_doc_receptor, datos.receptor_nombre,
                datos.tipo_doc_receptor, datos.nro_doc_receptor,
                datos.tipo_comprobante, datos.punto_venta,
                resultado['numero'], resultado['numero'],
                resultado.get('fecha_emision', date.today().strftime('%Y%m%d')),
                resultado.get('importe_total', 0),
                resultado.get('importe_neto', 0),
                resultado.get('importe_iva', 0),
                datos.concepto, datos.fecha_serv_desde, datos.fecha_serv_hasta,
                datos.fecha_vto_pago,
                resultado.get('cae'), resultado.get('cae_vto'),
                resultado.get('estado', 'R'),
                json.dumps(resultado.get('observaciones', [])),
                items_json,
            ))

        if resultado.get('success'):
            flash(f'CAE obtenido: {resultado["cae"]}', 'success')
        else:
            errores = resultado.get('errores', ['Error desconocido'])
            flash(f'Comprobante rechazado: {"; ".join(errores)}', 'error')

        # Reload ultimos
        with get_cursor() as cur:
            cur.execute("""
                SELECT * FROM comprobantes_emitidos
                WHERE estudio_id = %s ORDER BY created_at DESC LIMIT 10
            """, (estudio_id,))
            ultimos = cur.fetchall()
        for u in ultimos:
            u['tipo_desc'] = TIPOS_COMPROBANTE.get(u['tipo_comprobante'], '')

        return render_template('emitir_factura.html', resultado=resultado, ultimos=ultimos)

    except Exception as e:
        flash(f'Error al emitir: {str(e)}', 'error')
        return redirect(url_for('emitir_factura'))

    finally:
        import os as _os
        if _os.path.exists(cert_tmp.name):
            _os.unlink(cert_tmp.name)
        if _os.path.exists(key_tmp.name):
            _os.unlink(key_tmp.name)


# ══════════════════════════════════════════════════════════════════════════════
# MONOTRIBUTO — monitor de categorías y alertas
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/monotributo')
@login_required
@role_required('admin', 'contador')
def monotributo_monitor():
    """Dashboard de monitoreo de monotributistas del estudio."""
    from src.monotributo import get_todas_categorias, calcular_posicion
    from decimal import Decimal

    estudio_id = g.user['estudio_id']

    with get_cursor() as cur:
        cur.execute("""
            SELECT c.id, c.apellido, c.nombres, c.cuit, c.categoria_monotributo,
                   COALESCE(SUM(mf.monto_facturado), 0) AS facturado_12m,
                   COUNT(DISTINCT mf.periodo) AS meses_datos
            FROM clientes c
            LEFT JOIN monotributo_facturacion mf
                ON mf.cliente_id = c.id
                AND mf.periodo >= TO_CHAR(NOW() - INTERVAL '12 months', 'YYYY-MM')
            WHERE c.estudio_id = %s
              AND c.condicion_iva = 'Monotributo'
            GROUP BY c.id
            ORDER BY c.apellido, c.nombres
        """, (estudio_id,))
        clientes_mt = cur.fetchall()

    monitores = []
    for cli in clientes_mt:
        cat = cli['categoria_monotributo'] or 'A'
        status = calcular_posicion(
            categoria=cat,
            facturado_12m=Decimal(str(cli['facturado_12m'])),
            meses_datos=cli['meses_datos'] or 0,
        )
        monitores.append({
            'cliente': cli,
            'status': {
                'categoria': status.categoria,
                'tope_anual': float(status.tope_anual),
                'facturado_12m': float(status.facturado_12m),
                'porcentaje': status.porcentaje,
                'alerta': status.alerta,
                'categoria_sugerida': status.categoria_sugerida,
                'meses_datos': status.meses_datos,
            },
        })

    categorias = get_todas_categorias()
    return render_template('monotributo_monitor.html',
                         monitores=monitores, categorias=categorias)


@app.route('/monotributo/registrar', methods=['POST'])
@login_required
@role_required('admin', 'contador')
def monotributo_registrar():
    """Registrar/actualizar facturación mensual de un monotributista."""
    estudio_id = g.user['estudio_id']
    cliente_id = request.form.get('cliente_id', type=int)
    periodo = request.form.get('periodo', '').strip()  # YYYY-MM
    monto = request.form.get('monto', '0').strip()

    if not cliente_id or not periodo:
        flash('Cliente y período son obligatorios.', 'error')
        return redirect(url_for('monotributo_monitor'))

    try:
        from decimal import Decimal
        monto_dec = Decimal(monto.replace('.', '').replace(',', '.'))

        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO monotributo_facturacion (estudio_id, cliente_id, periodo, monto_facturado, cantidad_comp)
                VALUES (%s, %s, %s, %s, 1)
                ON CONFLICT (estudio_id, cliente_id, periodo)
                DO UPDATE SET monto_facturado = EXCLUDED.monto_facturado, updated_at = NOW()
            """, (estudio_id, cliente_id, periodo, monto_dec))

        flash(f'Facturación {periodo} registrada correctamente.', 'success')
    except Exception as e:
        flash(f'Error al registrar: {e}', 'error')

    return redirect(url_for('monotributo_monitor'))


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENTOS — gestión documental (adjuntos)
# ══════════════════════════════════════════════════════════════════════════════

UPLOAD_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')

ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp',
    'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt', 'xml',
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/documentos')
@login_required
@role_required('admin', 'contador')
def documentos_lista():
    """Lista de documentos del estudio."""
    estudio_id = g.user['estudio_id']
    cliente_id = request.args.get('cliente_id', type=int)

    with get_cursor() as cur:
        if cliente_id:
            cur.execute("""
                SELECT d.*, c.apellido, c.nombres
                FROM documentos d
                LEFT JOIN clientes c ON c.id = d.cliente_id
                WHERE d.estudio_id = %s AND d.cliente_id = %s
                ORDER BY d.created_at DESC
            """, (estudio_id, cliente_id))
        else:
            cur.execute("""
                SELECT d.*, c.apellido, c.nombres
                FROM documentos d
                LEFT JOIN clientes c ON c.id = d.cliente_id
                WHERE d.estudio_id = %s
                ORDER BY d.created_at DESC
                LIMIT 100
            """, (estudio_id,))
        docs = cur.fetchall()

        cur.execute("""
            SELECT id, apellido, nombres, cuit FROM clientes
            WHERE estudio_id = %s ORDER BY apellido, nombres
        """, (estudio_id,))
        clientes = cur.fetchall()

    return render_template('documentos.html', documentos=docs, clientes=clientes,
                         cliente_id=cliente_id)


@app.route('/documentos/subir', methods=['POST'])
@login_required
@role_required('admin', 'contador')
def documentos_subir():
    """Subir un documento."""
    import uuid
    from datetime import datetime

    estudio_id = g.user['estudio_id']
    usuario_id = g.user['id']

    archivo = request.files.get('archivo')
    if not archivo or not archivo.filename:
        flash('Debe seleccionar un archivo.', 'error')
        return redirect(url_for('documentos_lista'))

    if not _allowed_file(archivo.filename):
        flash(f'Tipo de archivo no permitido. Permitidos: {", ".join(sorted(ALLOWED_EXTENSIONS))}', 'error')
        return redirect(url_for('documentos_lista'))

    # Leer y verificar tamaño
    contenido = archivo.read()
    if len(contenido) > MAX_FILE_SIZE:
        flash(f'El archivo excede el límite de {MAX_FILE_SIZE // (1024*1024)} MB.', 'error')
        return redirect(url_for('documentos_lista'))

    cliente_id = request.form.get('cliente_id', type=int) or None
    categoria = request.form.get('categoria', 'general')
    descripcion = request.form.get('descripcion', '').strip() or None

    # Generar nombre único y path
    ext = archivo.filename.rsplit('.', 1)[1].lower()
    nombre_storage = f"{uuid.uuid4().hex}.{ext}"
    year = datetime.now().strftime('%Y')
    ruta_rel = os.path.join(str(estudio_id), year, nombre_storage)
    ruta_abs = os.path.join(UPLOAD_BASE, ruta_rel)

    os.makedirs(os.path.dirname(ruta_abs), exist_ok=True)
    with open(ruta_abs, 'wb') as f:
        f.write(contenido)

    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO documentos
                    (estudio_id, cliente_id, nombre_original, nombre_storage,
                     ruta_storage, mime_type, tamano_bytes, categoria,
                     descripcion, subido_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (estudio_id, cliente_id, archivo.filename, nombre_storage,
                  ruta_rel, archivo.content_type, len(contenido), categoria,
                  descripcion, usuario_id))

        flash(f'Documento "{archivo.filename}" subido correctamente.', 'success')
    except Exception as e:
        if os.path.exists(ruta_abs):
            os.remove(ruta_abs)
        flash(f'Error al guardar documento: {e}', 'error')

    redir = url_for('documentos_lista')
    if cliente_id:
        redir += f'?cliente_id={cliente_id}'
    return redirect(redir)


@app.route('/documentos/<int:doc_id>/descargar')
@login_required
@role_required('admin', 'contador', 'readonly')
def documentos_descargar(doc_id):
    """Descargar un documento."""
    estudio_id = g.user['estudio_id']
    with get_cursor() as cur:
        cur.execute("""
            SELECT ruta_storage, nombre_original, mime_type
            FROM documentos WHERE id = %s AND estudio_id = %s
        """, (doc_id, estudio_id))
        doc = cur.fetchone()

    if not doc:
        flash('Documento no encontrado.', 'error')
        return redirect(url_for('documentos_lista'))

    ruta_abs = os.path.join(UPLOAD_BASE, doc['ruta_storage'])
    if not os.path.exists(ruta_abs):
        flash('El archivo no existe en el servidor.', 'error')
        return redirect(url_for('documentos_lista'))

    return send_file(ruta_abs, download_name=doc['nombre_original'],
                     mimetype=doc['mime_type'], as_attachment=True)


@app.route('/documentos/<int:doc_id>/eliminar', methods=['POST'])
@login_required
@role_required('admin')
def documentos_eliminar(doc_id):
    """Eliminar un documento."""
    estudio_id = g.user['estudio_id']
    with get_cursor() as cur:
        cur.execute("""
            SELECT ruta_storage, cliente_id FROM documentos
            WHERE id = %s AND estudio_id = %s
        """, (doc_id, estudio_id))
        doc = cur.fetchone()

        if not doc:
            flash('Documento no encontrado.', 'error')
            return redirect(url_for('documentos_lista'))

        cur.execute("DELETE FROM documentos WHERE id = %s AND estudio_id = %s",
                    (doc_id, estudio_id))

    ruta_abs = os.path.join(UPLOAD_BASE, doc['ruta_storage'])
    if os.path.exists(ruta_abs):
        os.remove(ruta_abs)

    flash('Documento eliminado.', 'success')
    redir = url_for('documentos_lista')
    if doc['cliente_id']:
        redir += f'?cliente_id={doc["cliente_id"]}'
    return redirect(redir)


# ══════════════════════════════════════════════════════════════════════════════
# PADRÓN ARCA — consulta de contribuyentes
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/padron')
@login_required
@role_required('admin', 'contador')
def padron_arca():
    """Página de consulta del Padrón ARCA."""
    return render_template('padron_arca.html')


# ══════════════════════════════════════════════════════════════════════════════
# RETENCIONES — calculadora y registro
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/retenciones')
@login_required
@role_required('admin', 'contador')
def retenciones_lista():
    """Módulo de retenciones: calculadora + listado."""
    estudio_id = g.user['estudio_id']
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM retenciones
            WHERE estudio_id = %s
            ORDER BY fecha DESC LIMIT 50
        """, (estudio_id,))
        retenciones = cur.fetchall()
    return render_template('retenciones.html', retenciones=retenciones)


@app.route('/retenciones/registrar', methods=['POST'])
@login_required
@role_required('admin', 'contador')
def retenciones_registrar():
    """Registrar una retención sufrida o practicada."""
    estudio_id = g.user['estudio_id']
    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO retenciones
                    (estudio_id, tipo, impuesto, cuit_agente, nombre_agente,
                     fecha, nro_certificado, importe_retenido, jurisdiccion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                estudio_id,
                request.form.get('tipo'),
                request.form.get('impuesto'),
                request.form.get('cuit_agente', '').replace('-', '').replace(' ', ''),
                request.form.get('nombre_agente', '').strip() or None,
                request.form.get('fecha'),
                request.form.get('nro_certificado', '').strip() or None,
                request.form.get('importe_retenido'),
                request.form.get('jurisdiccion', '').strip() or None,
            ))
        flash('Retención registrada.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('retenciones_lista'))


# ══════════════════════════════════════════════════════════════════════════════
# COBROS Y PAGOS — cuentas corrientes
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/cobros-pagos')
@login_required
@role_required('admin', 'contador')
def cobros_pagos():
    """Cuentas corrientes y aging."""
    from src.cobros_pagos import obtener_cuentas, aging_report
    estudio_id = g.user['estudio_id']
    tipo = request.args.get('tipo', 'cliente')

    with get_cursor() as cur:
        cuentas = obtener_cuentas(cur, estudio_id, tipo)
        aging = aging_report(cur, estudio_id, tipo)

    return render_template('cobros_pagos.html', cuentas=cuentas, aging=aging, tipo=tipo)


@app.route('/cobros-pagos/crear', methods=['POST'])
@login_required
@role_required('admin', 'contador')
def cc_crear():
    """Crear cuenta corriente."""
    estudio_id = g.user['estudio_id']
    nombre = request.form.get('nombre', '').strip()
    cuit = request.form.get('cuit', '').strip().replace('-', '').replace(' ', '') or None
    tipo = request.form.get('tipo', 'cliente')

    if not nombre:
        flash('El nombre es obligatorio.', 'error')
        return redirect(url_for('cobros_pagos', tipo=tipo))

    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO cuentas_corrientes (estudio_id, nombre, cuit, tipo)
                VALUES (%s, %s, %s, %s)
            """, (estudio_id, nombre, cuit, tipo))
        flash(f'Cuenta de {nombre} creada.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('cobros_pagos', tipo=tipo))


@app.route('/cobros-pagos/movimiento', methods=['POST'])
@login_required
@role_required('admin', 'contador')
def cc_movimiento():
    """Registrar movimiento en cuenta corriente."""
    from src.cobros_pagos import registrar_movimiento
    from decimal import Decimal

    estudio_id = g.user['estudio_id']
    cuenta_id = request.form.get('cuenta_id', type=int)
    tipo_mov = request.form.get('tipo_mov')
    fecha = request.form.get('fecha')
    monto = Decimal(request.form.get('monto', '0'))
    descripcion = request.form.get('descripcion', '').strip()

    # Facturas y ND son debe, cobros/pagos y NC son haber
    if tipo_mov in ('factura', 'nota_debito'):
        debe, haber = monto, Decimal('0')
    else:
        debe, haber = Decimal('0'), monto

    try:
        with get_cursor() as cur:
            registrar_movimiento(cur, cuenta_id, estudio_id, fecha,
                                tipo_mov, debe, haber, descripcion)
        flash('Movimiento registrado.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('cobros_pagos'))


# ══════════════════════════════════════════════════════════════════════════════
# INGRESOS BRUTOS — CM03/CM05
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/iibb')
@login_required
@role_required('admin', 'contador')
def iibb_dashboard():
    """Dashboard de Ingresos Brutos."""
    estudio_id = g.user['estudio_id']

    with get_cursor() as cur:
        cur.execute("""
            SELECT id, apellido, nombres, cuit FROM clientes
            WHERE estudio_id = %s AND condicion_iva = 'IVA Responsable Inscripto'
            ORDER BY apellido, nombres
        """, (estudio_id,))
        clientes = cur.fetchall()

        cur.execute("""
            SELECT * FROM iibb_declaraciones
            WHERE estudio_id = %s
            ORDER BY periodo DESC LIMIT 20
        """, (estudio_id,))
        declaraciones = cur.fetchall()

    return render_template('iibb.html', clientes=clientes,
                         declaraciones=declaraciones, cm03=None)


@app.route('/iibb/cm03', methods=['POST'])
@login_required
@role_required('admin', 'contador')
def iibb_cm03():
    """Calcular CM03 para un cliente y período."""
    from src.iibb import calcular_cm03
    estudio_id = g.user['estudio_id']
    cliente_id = request.form.get('cliente_id', type=int)
    periodo = request.form.get('periodo', '').strip()

    cm03 = None
    try:
        with get_cursor() as cur:
            cm03 = calcular_cm03(cur, estudio_id, cliente_id, periodo)

            # Listar clientes para el form
            cur.execute("""
                SELECT id, apellido, nombres, cuit FROM clientes
                WHERE estudio_id = %s AND condicion_iva = 'IVA Responsable Inscripto'
                ORDER BY apellido, nombres
            """, (estudio_id,))
            clientes = cur.fetchall()

            cur.execute("""
                SELECT * FROM iibb_declaraciones
                WHERE estudio_id = %s ORDER BY periodo DESC LIMIT 20
            """, (estudio_id,))
            declaraciones = cur.fetchall()

    except Exception as e:
        flash(f'Error calculando CM03: {e}', 'error')
        clientes = []
        declaraciones = []

    return render_template('iibb.html', clientes=clientes,
                         declaraciones=declaraciones, cm03=cm03)


@app.route('/padron/consultar')
@login_required
@role_required('admin', 'contador')
def padron_consultar():
    """API: consulta un CUIT en el padrón público de ARCA."""
    from src.padron_arca import consultar_padron_publico

    cuit = request.args.get('cuit', '').strip()
    if not cuit:
        return jsonify({'error': 'Debe ingresar un CUIT'}), 400

    resultado = consultar_padron_publico(cuit)
    if resultado.get('error'):
        return jsonify(resultado), 400

    return jsonify(resultado), 200


if __name__ == '__main__':
    app.run(debug=True)

