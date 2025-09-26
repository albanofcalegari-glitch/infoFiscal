
# --- IMPORTS Y DEFINICIÓN DE APP AL INICIO ---
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from pathlib import Path
import sqlite3
import bcrypt
import os

app = Flask(__name__)
app.secret_key = 'cambia-esto-por-una-clave-segura'

# Endpoint para descargar facturas emitidas por CUIT
@app.route('/descargar-facturas')
def descargar_facturas():
    if 'usuario' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    cuit = request.args.get('cuit')
    if not cuit:
        return jsonify({'error': 'CUIT requerido'}), 400

    # Carpeta destino para facturas
    facturas_dir = Path(__file__).parent.parent / 'facturas' / cuit
    os.makedirs(facturas_dir, exist_ok=True)

    # --- Integración con ARCA/AFIP (versión simplificada) ---
    try:
        from arca_service_simple import descargar_facturas_arca_simple
        
        # Intentar descargar facturas (modo real si están habilitados los servicios)
        # Tu CUIT (20321518045) puede consultar CUITs delegados por otros contribuyentes
        archivos_descargados = descargar_facturas_arca_simple(
            cuit, 
            output_dir=facturas_dir, 
            modo_real=False,  # Cambiar a True cuando se activen los servicios
            consultar_como="20321518045"  # Tu CUIT que tiene las delegaciones
        )
        
        if not archivos_descargados:
            # Si no hay facturas, crear archivo informativo
            info_path = facturas_dir / 'sin_facturas.txt'
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write(f'No se encontraron facturas para CUIT {cuit} en el período consultado.\n')
                f.write(f'Fecha de consulta: {Path(__file__).stat().st_mtime}\n')
        
    except FileNotFoundError as e:
        # Certificados no configurados - usar modo demo
        demo_path = facturas_dir / 'DEMO_facturas.txt'
        with open(demo_path, 'w', encoding='utf-8') as f:
            f.write(f'MODO DEMO - Certificados AFIP no configurados\n')
            f.write(f'CUIT consultado: {cuit}\n')
            f.write(f'Para usar ARCA real, seguir instrucciones en certs/README.md\n')
            f.write(f'Error: {str(e)}\n')
    
    except Exception as e:
        # Error en consulta - crear archivo de error
        error_path = facturas_dir / 'error_descarga.txt'
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write(f'Error al consultar ARCA/AFIP para CUIT {cuit}\n')
            f.write(f'Error: {str(e)}\n')
            f.write(f'Revisar configuración de certificados y conectividad.\n')

    # Comprimir la carpeta en un ZIP para descargar
    import shutil
    zip_base = facturas_dir.parent / f'facturas_{cuit}'
    zip_path = Path(str(zip_base) + '.zip')
    shutil.make_archive(str(zip_base), 'zip', facturas_dir)

    # Verificar que el archivo ZIP existe antes de enviarlo
    if not zip_path.exists():
        return jsonify({'error': 'No se pudo generar el archivo ZIP'}), 500

    # Enviar el ZIP como descarga
    return send_file(str(zip_path), as_attachment=True)

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
    if request.method == 'POST':
        tipoDocumento = request.form['tipoDocumento']
        nroDocumento = request.form['nroDocumento']
        CUIT = request.form['CUIT']
        apellido = request.form['apellido']
        nombres = request.form['nombres']
        fechaNacimiento = request.form['fechaNacimiento']
        condicionIVA = request.form['condicionIVA']
        categoriaMonotriibuto = request.form['categoriaMonotriibuto']
        db_path = Path(__file__).parent.parent / 'infofiscal.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO clientes (tipoDocumento, nroDocumento, CUIT, apellido, nombres, fechaNacimiento, condicionIVA, categoriaMonotriibuto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tipoDocumento, nroDocumento, CUIT, apellido, nombres, fechaNacimiento, condicionIVA, categoriaMonotriibuto))
        conn.commit()
        conn.close()
        mensaje = 'Cliente creado exitosamente.'
    return render_template('nuevo_cliente.html', usuario=session['usuario'], mensaje=mensaje)

# Ruta para consultar cliente por CUIT o DNI (AJAX)
@app.route('/consultar-cliente', methods=['GET'])
def consultar_cliente():
    if 'usuario' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    busqueda = request.args.get('busqueda', '').strip()
    if not busqueda:
        return jsonify({'error': 'Debe ingresar CUIT o DNI'}), 400
    db_path = Path(__file__).parent.parent / 'infofiscal.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''SELECT tipoDocumento, nroDocumento, CUIT, apellido, nombres, fechaNacimiento, condicionIVA, categoriaMonotriibuto FROM clientes WHERE CUIT = ? OR nroDocumento = ?''', (busqueda, busqueda))
    row = cursor.fetchone()
    conn.close()
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
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT contrasena, bloqueado, cantidadDeIntentos FROM usuario WHERE usuario = ?', (usuario,))
        row = cursor.fetchone()
        if row:
            hashed, bloqueado, intentos = row
            if bloqueado:
                error = 'Usuario bloqueado.'
            elif bcrypt.checkpw(contrasena.encode('utf-8'), hashed):
                # Login exitoso: resetear intentos
                cursor.execute('UPDATE usuario SET cantidadDeIntentos = 0, fechaUltimoLogin = datetime("now") WHERE usuario = ?', (usuario,))
                conn.commit()
                session['usuario'] = usuario
                conn.close()
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
                conn.close()
        else:
            conn.close()
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
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if request.method == 'POST':
            user_to_unlock = request.form.get('user_to_unlock')
            if user_to_unlock:
                cursor.execute('UPDATE usuario SET bloqueado = 0, cantidadDeIntentos = 0 WHERE usuario = ?', (user_to_unlock,))
                conn.commit()
                desbloqueado = user_to_unlock
        cursor.execute('SELECT usuario FROM usuario WHERE bloqueado = 1')
        usuarios_bloqueados = [row[0] for row in cursor.fetchall()]
        conn.close()
    return render_template('index.html', usuario=usuario, usuarios_bloqueados=usuarios_bloqueados, desbloqueado=desbloqueado)

if __name__ == '__main__':
    app.run(debug=True)
