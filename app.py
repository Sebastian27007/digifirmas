import os
import uuid
import base64 # Importado desde main, puede ser útil
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'secreto_super_seguro'  # Esencial para las sesiones

# Usaremos una sola carpeta de uploads para simplificar, ya que los archivos se asociarán por ID.
UPLOAD_FOLDER = 'uploads' 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Base de datos temporal de usuarios (de main)
usuarios = {
    "admin": {"password": "admin123", "email": "admin@mail.com"}
}

# --- RUTAS DE AUTENTICACIÓN (de main, sin cambios) ---

# Registro de usuario
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if username in usuarios:
            flash("El usuario ya existe.")
        else:
            usuarios[username] = {'password': password, 'email': email}
            flash("Registro exitoso. Ahora inicia sesión.")
            return redirect(url_for('login'))
    return render_template('register.html')

# Login de usuario
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = usuarios.get(username)
        if user and user['password'] == password:
            session['username'] = username
            return redirect(url_for('index')) # Redirige al index (la página de firma)
        else:
            flash("Credenciales incorrectas.")
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Sesión cerrada correctamente.")
    return redirect(url_for('login'))

# --- RUTAS DE LA APLICACIÓN PRINCIPAL ---

# Página principal (el digitalizador de firmas)
@app.route('/')
def index():
    # Protegemos la ruta: si no hay sesión, se va al login.
    if 'username' not in session:
        flash("Por favor, inicia sesión para acceder a esta página.")
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

# --- NUEVA RUTA DE SUBIDA (Tu lógica, adaptada y mejorada) ---
# Esta única ruta reemplaza a /save_signature, /upload_signature y el viejo /upload_document de main.
@app.route('/upload_document', methods=['POST'])
def upload_document_and_signature():
    # 1. Seguridad: Verificar que el usuario tenga sesión iniciada
    if 'username' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401 # 401 Unauthorized es mejor para APIs

    # 2. Validaciones de archivos (tu lógica)
    if 'document_file' not in request.files or 'signature_file' not in request.files:
        return jsonify({'error': 'Petición inválida, faltan archivos'}), 400

    document = request.files['document_file']
    signature = request.files['signature_file']

    if document.filename == '' or signature.filename == '':
        return jsonify({'error': 'No se seleccionaron todos los archivos necesarios'}), 400

    # 3. Lógica de asociación (Tu lógica + la de main)
    if document and signature:
        # Limpiamos los nombres de los archivos
        secure_doc_name = secure_filename(document.filename)
        secure_sig_name = secure_filename(signature.filename)
        
        # Creamos un nombre de archivo que incluye el usuario Y un ID único
        # Esto nos da lo mejor de ambos mundos: sabemos QUIÉN lo subió y QUÉ firma va con QUÉ documento.
        unique_id = str(uuid.uuid4().hex)[:8] # Un ID corto
        username = session['username']
        
        doc_filename = f"{username}_{unique_id}_{secure_doc_name}"
        sig_filename = f"{username}_{unique_id}_{secure_sig_name}"

        # Guardamos los archivos
        doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
        sig_path = os.path.join(app.config['UPLOAD_FOLDER'], sig_filename)
        
        document.save(doc_path)
        signature.save(sig_path)

        # Devolvemos una respuesta exitosa al frontend
        return jsonify({
            'message': 'Documento y firma subidos y asociados con éxito',
            'file_path': doc_filename
        }), 200

    return jsonify({'error': 'Ocurrió un error inesperado'}), 500


# --- INICIAR EL SERVIDOR ---
if __name__ == '__main__':
    app.run(debug=True)