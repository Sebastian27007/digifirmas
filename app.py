import os
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secreto_super_seguro'  # Cámbialo en producción

# Carpetas de subida
UPLOAD_FOLDER = 'uploads/firmas'
DOCUMENT_FOLDER = 'uploads/documentos'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCUMENT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOCUMENT_FOLDER'] = DOCUMENT_FOLDER

# Base de datos temporal de usuarios (diccionario en memoria)
usuarios = {
    "admin": {"password": "admin123", "email": "admin@mail.com"}
}

# ---------------- RUTAS ----------------

# Página principal: canvas de firma
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# Guardar firma desde el canvas
@app.route('/save_signature', methods=['POST'])
def save_signature():
    if 'username' not in session:
        return redirect(url_for('login'))

    data_url = request.form['imageData']
    header, encoded = data_url.split(",", 1)
    data = base64.b64decode(encoded)

    filename = f"{session['username']}_firma.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(filepath, 'wb') as f:
        f.write(data)

    return 'Firma guardada correctamente.'

# Subir una imagen de firma
@app.route('/upload_signature', methods=['POST'])
def upload_signature():
    if 'username' not in session:
        return redirect(url_for('login'))

    file = request.files.get('signatureImage')
    if file and file.filename != '':
        filename = secure_filename(session['username'] + '_' + file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return 'Imagen subida correctamente.'
    return 'No se seleccionó ningún archivo.'

# Subir un documento (extra opcional)
@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'username' not in session:
        return redirect(url_for('login'))

    file = request.files.get('document')
    if file and file.filename != '':
        filename = secure_filename(session['username'] + '_' + file.filename)
        filepath = os.path.join(app.config['DOCUMENT_FOLDER'], filename)
        file.save(filepath)
        return 'Documento subido correctamente.'
    return 'No se seleccionó ningún archivo.'

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
            return redirect(url_for('dashboard'))
        else:
            flash("Credenciales incorrectas.")

    return render_template('login.html')

# Dashboard del usuario
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    firmas = [
        f for f in os.listdir(app.config['UPLOAD_FOLDER'])
        if f.startswith(username)
    ]
    documentos = [
        d for d in os.listdir(app.config['DOCUMENT_FOLDER'])
        if d.startswith(username)
    ]

    return render_template('dashboard.html', username=username, firmas=firmas, documentos=documentos)

# Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Sesión cerrada correctamente.")
    return redirect(url_for('login'))

# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True)
