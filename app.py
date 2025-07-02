import os
import uuid
import json  # <-- NUEVO: Para manejar la base de datos en JSON
import time  # <-- NUEVO: Para generar IDs únicos para las firmas

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
app = Flask(__name__)
app.secret_key = 'secreto_super_seguro'

UPLOAD_FOLDER = 'uploads' 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_FILE = 'database.json' # <-- NUEVO: El nombre de nuestro archivo de base de datos

# --- FUNCIONES AUXILIARES PARA LA "BASE DE DATOS" JSON ---

def load_db():
    """Carga la base de datos desde el archivo JSON. Si no existe, la crea vacía."""
    if not os.path.exists(DB_FILE):
        # Estructura inicial de nuestra base de datos
        return {'users': {"admin": {"password": "admin123"}}, 'signatures': {}}
    with open(DB_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Si el archivo está vacío o corrupto, empezamos de nuevo
            return {'users': {"admin": {"password": "admin123"}}, 'signatures': {}}

def save_db(data):
    """Guarda los datos en el archivo JSON."""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- RUTAS DE AUTENTICACIÓN (Adaptadas para usar la base de datos JSON) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db_data = load_db() # Carga la base de datos
        username = request.form['username']
        password = request.form['password']
        if username in db_data['users']:
            flash("El usuario ya existe.")
        else:
            db_data['users'][username] = {'password': password}
            save_db(db_data) # Guarda el nuevo usuario
            flash("Registro exitoso. Ahora inicia sesión.")
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db_data = load_db() # Carga la base de datos
        username = request.form['username']
        password = request.form['password']
        user = db_data['users'].get(username)
        if user and user['password'] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash("Credenciales incorrectas.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Sesión cerrada correctamente.")
    return redirect(url_for('login'))

# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

# --- NUEVA API PARA GESTIÓN DE FIRMAS (Usando JSON) ---

# [GET] Esta ruta le dará al frontend la lista de firmas guardadas del usuario.
@app.route('/api/signatures', methods=['GET'])
def get_signatures():
    if 'username' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    db_data = load_db()
    # Busca las firmas del usuario actual. Si no tiene, devuelve una lista vacía.
    user_signatures = db_data.get('signatures', {}).get(session['username'], [])
    return jsonify(user_signatures)

# [POST] Esta ruta guardará una nueva firma que el usuario dibuje y nombre.
@app.route('/api/signatures', methods=['POST'])
def save_new_signature():
    if 'username' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    file = request.files.get('signature_file')
    name = request.form.get('signature_name')

    if not file or not name:
        return jsonify({'error': 'Faltan datos (archivo o nombre)'}), 400

    username = session['username']
    db_data = load_db()

    # Guardar el archivo de la firma en el disco
    filename = f"{username}_{secure_filename(name)}_{int(time.time())}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Crear el registro de la nueva firma
    new_sig = {
        'id': int(time.time() * 1000), # Usamos el tiempo como un ID único y simple
        'name': name,
        'path': f"/uploads/{filename}" # Guardamos la ruta para que el frontend la pueda usar
    }

    # Añadir la firma a la lista del usuario en nuestra "base de datos"
    if username not in db_data['signatures']:
        db_data['signatures'][username] = []
    db_data['signatures'][username].append(new_sig)
    save_db(db_data)

    return jsonify({'message': 'Firma guardada con éxito', 'signature': new_sig}), 201

# --- RUTA DE SUBIDA PRINCIPAL (Por ahora, sin cambios) ---
@app.route('/upload_document', methods=['POST'])
def upload_document_and_signature():
    # Esta ruta seguirá funcionando para el flujo principal.
    # Más adelante la adaptaremos para que pueda recibir una firma guardada.
    if 'username' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    if 'document_file' not in request.files or 'signature_file' not in request.files:
        return jsonify({'error': 'Petición inválida, faltan archivos'}), 400

    document = request.files['document_file']
    signature = request.files['signature_file']

    if document.filename == '' or signature.filename == '':
        return jsonify({'error': 'No se seleccionaron todos los archivos necesarios'}), 400

    if document and signature:
        secure_doc_name = secure_filename(document.filename)
        secure_sig_name = secure_filename(signature.filename)
        unique_id = str(uuid.uuid4().hex)[:8]
        username = session['username']
        
        doc_filename = f"{username}_{unique_id}_{secure_doc_name}"
        sig_filename = f"{username}_{unique_id}_{secure_sig_name}"

        doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
        sig_path = os.path.join(app.config['UPLOAD_FOLDER'], sig_filename)
        
        document.save(doc_path)
        signature.save(sig_path)

        return jsonify({
            'message': 'Documento y firma subidos y asociados con éxito',
            'file_path': doc_filename 
        }), 200

    return jsonify({'error': 'Ocurrió un error inesperado'}), 500


# --- INICIAR EL SERVIDOR ---
if __name__ == '__main__':
    app.run(debug=True)