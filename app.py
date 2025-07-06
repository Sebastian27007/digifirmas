import os
import uuid
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv  # <-- 1. Importar dotenv
from supabase import create_client, Client # <-- 2. Importar supabase

# Cargar variables de entorno del archivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = 'secreto_super_seguro'

UPLOAD_FOLDER = 'uploads' 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- 3. CONFIGURACIÓN DE SUPABASE ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# La base de datos de usuarios en memoria se elimina. ¡Ya no la necesitamos!
# usuarios = { ... } <-- ELIMINAR ESTE DICCIONARIO

# --- RUTAS DE AUTENTICACIÓN (Modificadas para Supabase) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'] # Mantenemos el username para la sesión
        email = request.form['email']
        password = request.form['password']

        try:
            # 4. Usar Supabase para registrar al usuario
            user = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "username": username
                    }
                }
            })
            flash("Registro exitoso. Revisa tu correo para verificar tu cuenta. Luego inicia sesión.")
            return redirect(url_for('login'))
        except Exception as e:
            # Manejo de errores de Supabase (ej: usuario ya existe)
            flash(f"Error en el registro: {e}")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'] # El login en Supabase es con email
        password = request.form['password']

        try:
            # 5. Usar Supabase para iniciar sesión
            data = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            # Guardamos el token de acceso y los datos del usuario en la sesión de Flask
            session['user'] = data.user.dict()
            session['access_token'] = data.session.access_token
            
            # Para mantener la personalización, extraemos el username guardado
            username = data.user.user_metadata.get('username', email)
            session['username'] = username # <-- Guardamos el username para mostrarlo
            
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Credenciales incorrectas: {e}")

    return render_template('login.html') # <-- Asegúrate de pedir el email en tu plantilla de login

@app.route('/logout')
def logout():
    # 6. Limpiar la sesión de Flask
    session.pop('user', None)
    session.pop('username', None)
    session.pop('access_token', None)
    flash("Sesión cerrada correctamente.")
    return redirect(url_for('login'))

# --- RUTA PRINCIPAL (Modificada para usar la nueva sesión) ---
@app.route('/')
def index():
    if 'user' not in session: # Usamos 'user' como verificador principal
        flash("Por favor, inicia sesión para acceder a esta página.")
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username'))

# --- RUTA DE SUBIDA (Modificada para guardar en la tabla 'documentos') ---
@app.route('/upload_document', methods=['POST'])
def upload_document_and_signature():
    if 'user' not in session:
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

        # 7. Insertar registro en la tabla 'documentos' de Supabase
        try:
            user_id = session['user']['id']
            supabase.table('documentos').insert({
                "user_id": user_id,
                "doc_filename": doc_filename,
                "sig_filename": sig_filename
            }).execute()
        except Exception as e:
            # Si falla la inserción en BD, es importante manejarlo
            # Podríamos borrar los archivos guardados para mantener consistencia
            os.remove(doc_path)
            os.remove(sig_path)
            return jsonify({'error': f'Error al guardar en la base de datos: {e}'}), 500

        return jsonify({
            'message': 'Documento y firma subidos y asociados con éxito',
            'file_path': doc_filename
        }), 200

    return jsonify({'error': 'Ocurrió un error inesperado'}), 500

if __name__ == '__main__':
    app.run(debug=True)