
# --- IMPORTS OPTIMIZADOS ---
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from pathlib import Path
import os

# Cargar variables de entorno del archivo .env
try:
    from dotenv import load_dotenv
    # Cargar .env desde el directorio padre (donde está el .env)
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"✅ Archivo .env cargado desde: {env_path}")
    print(f"🔧 INFOFISCAL_MODE: {os.environ.get('INFOFISCAL_MODE', 'No configurado')}")
except ImportError:
    print("⚠️ python-dotenv no disponible")

app = Flask(__name__)
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
    return render_template('index.html', usuario=usuario, usuarios_bloqueados=usuarios_bloqueados, desbloqueado=desbloqueado)

if __name__ == '__main__':
    app.run(debug=True)
