import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image # NECESARIO: pip install Pillow
import io # Para manejar streams de bytes

app = Flask(__name__)
app.secret_key = 'secreto_super_seguro'  # Esencial para las sesiones

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SIGNATURES_SUBFOLDER'] = os.path.join(UPLOAD_FOLDER, 'firmas')
app.config['SIGNED_DOCUMENTS_SUBFOLDER'] = os.path.join(UPLOAD_FOLDER, 'documentos_firmados')

os.makedirs(app.config['SIGNATURES_SUBFOLDER'], exist_ok=True)
os.makedirs(app.config['SIGNED_DOCUMENTS_SUBFOLDER'], exist_ok=True)

# Base de datos temporal de usuarios (en memoria)
usuarios = {
    "admin": {"password": "admin123", "email": "admin@mail.com", "firmas_guardadas": []}
}

# --- RUTAS DE AUTENTICACIÓN ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if username in usuarios:
            flash("El usuario ya existe.")
        else:
            usuarios[username] = {'password': password, 'email': email, 'firmas_guardadas': []} # Inicializar firmas
            flash("Registro exitoso. Ahora inicia sesión.")
            return redirect(url_for('login'))
    return render_template('register.html')

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

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Sesión cerrada correctamente.")
    return redirect(url_for('login'))

# --- RUTAS DE LA APLICACIÓN PRINCIPAL ---

# Página principal (el digitalizador de firmas para GUARDAR firmas)
@app.route('/')
def index():
    if 'username' not in session:
        flash("Por favor, inicia sesión para acceder a esta página.")
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

# Dashboard para listar firmas y firmar documentos existentes
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash("Por favor, inicia sesión para acceder al dashboard.")
        return redirect(url_for('login'))
    
    username = session['username']
    firmas_urls = []
    for filename in usuarios[username].get('firmas_guardadas', []):
        firmas_urls.append(url_for('uploaded_file', filename=f'firmas/{filename}'))
    
    return render_template('dashboard.html', username=username, firmas=firmas_urls)

# --- RUTA PARA GUARDAR FIRMAS INDIVIDUALMENTE (Para reutilización, desde index.html) ---
@app.route('/upload_signature', methods=['POST'])
def upload_signature():
    if 'username' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    if 'signature_file' not in request.files:
        return jsonify({'error': 'No se encontró el archivo de firma'}), 400

    signature_file = request.files['signature_file']
    if signature_file.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo de firma'}), 400

    username = session['username']
    # Genera un ID único para cada firma, asociado al usuario
    unique_sig_id = str(uuid.uuid4().hex)[:12]
    # El nombre de archivo será algo como "admin_123abc456def_mi_firma.png"
    # Aseguramos un nombre de archivo seguro y único
    original_filename = secure_filename(signature_file.filename) if signature_file.filename else 'firma_dibujada.png'
    sig_filename = f"{username}_{unique_sig_id}_{original_filename}"
    sig_path = os.path.join(app.config['SIGNATURES_SUBFOLDER'], sig_filename)

    try:
        signature_file.save(sig_path)
        # Añadir la firma a la lista del usuario en nuestra "BD" temporal
        if username in usuarios:
            if 'firmas_guardadas' not in usuarios[username]:
                usuarios[username]['firmas_guardadas'] = []
            usuarios[username]['firmas_guardadas'].append(sig_filename)

        return jsonify({
            'message': 'Firma guardada con éxito para reutilización',
            'signature_url': url_for('uploaded_file', filename=f'firmas/{sig_filename}')
        }), 200
    except Exception as e:
        print(f"Error al guardar la firma: {e}") # Para depuración
        return jsonify({'error': f'Error al guardar la firma: {str(e)}'}), 500

# --- RUTA ORIGINAL '/upload_document' (AHORA MÁS SIMPLE, SOLO GUARDA) ---
# Esta ruta se mantiene, pero solo guarda el documento y la firma temporalmente.
# La firma NO se añade a la lista de firmas reutilizables de usuarios aquí.
# El usuario deberá ir al dashboard para firmar con una firma ya guardada.
@app.route('/upload_document', methods=['POST'])
def upload_document_from_index():
    if 'username' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    if 'document_file' not in request.files or 'signature_file' not in request.files:
        return jsonify({'error': 'Petición inválida, faltan archivos'}), 400

    document = request.files['document_file']
    signature = request.files['signature_file']

    if document.filename == '' or signature.filename == '':
        return jsonify({'error': 'No se seleccionaron todos los archivos necesarios'}), 400

    username = session['username']
    unique_id = str(uuid.uuid4().hex)[:8] # Un ID corto
    
    # Guardar el documento
    doc_filename = f"{username}_{unique_id}_doc_{secure_filename(document.filename)}"
    doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
    document.save(doc_path)

    # Guardar la firma (se guarda en la carpeta principal de uploads, no en la de firmas reutilizables)
    sig_filename = f"{username}_{unique_id}_sig_{secure_filename(signature.filename or 'firma_dibujada.png')}"
    sig_path = os.path.join(app.config['UPLOAD_FOLDER'], sig_filename)
    signature.save(sig_path)

    return jsonify({
        'message': 'Documento y firma subidos con éxito. Puedes firmar visualmente documentos en el Dashboard.',
        'document_path': url_for('uploaded_file', filename=doc_filename),
        'signature_path': url_for('uploaded_file', filename=sig_filename)
    }), 200

# --- RUTA PARA FIRMAR UN DOCUMENTO EXISTENTE (Desde dashboard.html) ---
@app.route('/sign_existing_document', methods=['POST'])
def sign_existing_document():
    if 'username' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    if 'document_file' not in request.files or 'signature_url' not in request.form:
        return jsonify({'error': 'Petición inválida, faltan datos o archivos'}), 400

    document_file = request.files['document_file']
    signature_url = request.form['signature_url']
    
    try:
        position_x = int(float(request.form.get('position_x', '0px').replace('px', '')))
        position_y = int(float(request.form.get('position_y', '0px').replace('px', '')))
        signature_width = int(float(request.form.get('signature_width', '100px').replace('px', '')))
        signature_height = int(float(request.form.get('signature_height', '50px').replace('px', '')))
        
    except ValueError as e:
        return jsonify({'error': f'Coordenadas o dimensiones inválidas: {str(e)}'}), 400

    # Extraer el nombre de archivo de la firma de la URL
    # Esto es crucial para acceder al archivo en la subcarpeta 'firmas'
    signature_filename = os.path.basename(signature_url) 
    signature_filepath = os.path.join(app.config['SIGNATURES_SUBFOLDER'], signature_filename)

    if not os.path.exists(signature_filepath):
        return jsonify({'error': f'La firma seleccionada no existe en el servidor: {signature_filepath}'}), 404

    try:
        doc_unique_id = str(uuid.uuid4().hex)[:8]
        original_doc_filename = secure_filename(document_file.filename)
        temp_doc_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{doc_unique_id}_{original_doc_filename}")
        document_file.save(temp_doc_path)

        signature_img = Image.open(signature_filepath).convert("RGBA")
        signature_img = signature_img.resize((signature_width, signature_height), Image.Resampling.LANCZOS)

        if original_doc_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            base_image = Image.open(temp_doc_path).convert("RGBA")
            overlay = Image.new('RGBA', base_image.size, (255, 255, 255, 0))
            
            paste_x = max(0, min(position_x, base_image.width - signature_img.width))
            paste_y = max(0, min(position_y, base_image.height - signature_img.height))

            overlay.paste(signature_img, (paste_x, paste_y), signature_img)
            signed_image = Image.alpha_composite(base_image, overlay)

            signed_filename = f"{session['username']}_signed_{doc_unique_id}_{original_doc_filename}"
            signed_filepath = os.path.join(app.config['SIGNED_DOCUMENTS_SUBFOLDER'], signed_filename)
            signed_image.save(signed_filepath)

            os.remove(temp_doc_path)

            return jsonify({
                'message': 'Documento imagen firmado con éxito',
                'file_path': url_for('uploaded_file', filename=f'documentos_firmados/{signed_filename}')
            }), 200

        elif original_doc_filename.lower().endswith('.pdf'):
            try:
                import fitz # PyMuPDF
                doc = fitz.open(temp_doc_path)
                if len(doc) == 0:
                    os.remove(temp_doc_path)
                    return jsonify({'error': 'El documento PDF no tiene páginas.'}), 400
                    
                page = doc[0] 

                img_byte_arr = io.BytesIO()
                signature_img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                rect_x0 = position_x
                rect_y0 = position_y
                rect_x1 = rect_x0 + signature_img.width
                rect_y1 = rect_y0 + signature_img.height
                
                page_rect = page.rect
                rect_x0 = max(0, min(rect_x0, page_rect.width - signature_img.width))
                rect_y0 = max(0, min(rect_y0, page_rect.height - signature_img.height))
                rect_x1 = rect_x0 + signature_img.width
                rect_y1 = rect_y0 + signature_img.height
                
                rect = fitz.Rect(rect_x0, rect_y0, rect_x1, rect_y1)
                
                page.insert_image(rect, stream=img_byte_arr, overlay=True)

                signed_filename = f"{session['username']}_signed_{doc_unique_id}_{original_doc_filename}"
                signed_filepath = os.path.join(app.config['SIGNED_DOCUMENTS_SUBFOLDER'], signed_filename)
                doc.save(signed_filepath)
                doc.close()
                os.remove(temp_doc_path)
                
                return jsonify({
                    'message': 'Documento PDF firmado con éxito',
                    'file_path': url_for('uploaded_file', filename=f'documentos_firmados/{signed_filename}')
                }), 200
            except ImportError:
                os.remove(temp_doc_path)
                return jsonify({'error': 'La librería PyMuPDF no está instalada para firmar PDFs. Instálala con: pip install PyMuPDF'}), 500
            except Exception as e:
                os.remove(temp_doc_path)
                print(f"Error al firmar PDF: {e}")
                return jsonify({'error': f'Error al firmar el PDF: {str(e)}. Asegúrate de que el PDF es válido y las coordenadas son correctas.'}), 500
        else:
            os.remove(temp_doc_path)
            return jsonify({'error': 'Tipo de documento no soportado para firmar. Solo imágenes (PNG, JPG, etc.) y PDFs.'}), 400

    except Exception as e:
        print(f"Error general en sign_existing_document: {e}")
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)