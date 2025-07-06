import os
import uuid
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from supabase import create_client, Client

# --- NUEVO: Importaciones para la manipulación de PDF e imágenes ---
import fitz  # PyMuPDF
from PIL import Image
import io

# Cargar variables de entorno del archivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'secreto_super_seguro_por_defecto')

# --- CONFIGURACIÓN DE CARPETA DE SUBIDAS ---
UPLOAD_FOLDER = 'instance/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- CONFIGURACIÓN DE SUPABASE ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- RUTAS DE AUTENTICACIÓN ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        try:
            res = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"username": username}}
            })
            
            if res.user:
                user_id = res.user.id
                supabase.table('usuarios').insert({
                    'id': user_id,
                    'username': username,
                    'email': email
                }).execute()

            flash("Registro exitoso. Revisa tu correo para verificar tu cuenta.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            # --- LÍNEA DE DEPURACIÓN AÑADIDA ---
            # Esta línea imprimirá el error exacto en tu terminal.
            print(f"ERROR DETALLADO DE REGISTRO: {e}")
            flash(f"Error en el registro. Por favor, revisa los datos.", "error")
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            data = supabase.auth.sign_in_with_password({"email": email, "password": password})
            session['user'] = data.user.dict()
            session['access_token'] = data.session.access_token
            username = data.user.user_metadata.get('username', email)
            session['username'] = username
            return redirect(url_for('dashboard'))
        except Exception as e:
            print(f"ERROR DETALLADO DE LOGIN: {e}")
            flash(f"Credenciales incorrectas.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('login'))

# --- RUTA PRINCIPAL Y PANEL DE CONTROL ---
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username'))

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Por favor, inicia sesión para acceder a esta página.", "warning")
        return redirect(url_for('login'))

    user_id = session['user']['id']
    firmas_urls = []
    try:
        response = supabase.table('user_signatures').select('filename').eq('supabase_user_id', user_id).execute()
        if response.data:
            for item in response.data:
                firmas_urls.append(url_for('serve_upload', filename=item['filename']))
    except Exception as e:
        print(f"ERROR DETALLADO DE DASHBOARD: {e}")
        flash(f"Error al cargar las firmas: {e}", "error")

    return render_template('dashboard.html', username=session.get('username'), firmas=firmas_urls)


# --- RUTAS DE SUBIDA Y FIRMA DE DOCUMENTOS ---

@app.route('/upload_signature', methods=['POST'])
def upload_signature():
    if 'user' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    if 'signature_file' not in request.files:
        return jsonify({'error': 'No se encontró el archivo de la firma'}), 400

    signature = request.files['signature_file']
    if signature.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400

    if signature:
        user_id = session['user']['id']
        username = session['username']
        unique_id = str(uuid.uuid4().hex)[:8]
        
        secure_sig_name = secure_filename(signature.filename)
        sig_filename = f"{username}_sig_{unique_id}_{secure_sig_name}"
        sig_path = os.path.join(app.config['UPLOAD_FOLDER'], sig_filename)
        signature.save(sig_path)

        try:
            supabase.table('user_signatures').insert({
                "supabase_user_id": user_id,
                "filename": sig_filename,
                "local_filepath": sig_path
            }).execute()

            signature_url = url_for('serve_upload', filename=sig_filename, _external=True)
            return jsonify({
                'message': 'Firma guardada con éxito.',
                'signature_url': signature_url
            }), 200
        except Exception as e:
            os.remove(sig_path)
            print(f"ERROR DETALLADO AL GUARDAR FIRMA: {e}")
            return jsonify({'error': f'Error al guardar en la base de datos: {e}'}), 500

    return jsonify({'error': 'Ocurrió un error inesperado'}), 500


@app.route('/sign_existing_document', methods=['POST'])
def sign_existing_document():
    if 'user' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    if 'document_file' not in request.files or 'signature_url' not in request.form:
        return jsonify({'error': 'Faltan datos para firmar el documento'}), 400

    document_file = request.files['document_file']
    signature_url = request.form['signature_url']
    
    pos_x_str = request.form.get('position_x', '0px').replace('px', '')
    pos_y_str = request.form.get('position_y', '0px').replace('px', '')
    sig_width_str = request.form.get('signature_width', '150px').replace('px', '')
    
    try:
        pos_x = float(pos_x_str)
        pos_y = float(pos_y_str)
        sig_width = int(float(sig_width_str))
    except ValueError:
        return jsonify({'error': 'Posición o tamaño de la firma inválidos'}), 400

    signature_filename = os.path.basename(signature_url)
    signature_path = os.path.join(app.config['UPLOAD_FOLDER'], signature_filename)

    if not os.path.exists(signature_path):
        return jsonify({'error': f'No se encontró el archivo de la firma: {signature_filename}'}), 404

    try:
        doc_stream = document_file.read()
        
        if document_file.mimetype == 'application/pdf':
            pdf_document = fitz.open(stream=doc_stream, filetype="pdf")
            page = pdf_document[0]
            
            preview_width = 800 
            scale_factor = page.rect.width / preview_width
            
            scaled_x = pos_x * scale_factor
            scaled_y = pos_y * scale_factor
            scaled_sig_width = sig_width * scale_factor
            
            signature_image = Image.open(signature_path)
            aspect_ratio = signature_image.height / signature_image.width
            scaled_sig_height = scaled_sig_width * aspect_ratio
            
            sig_rect = fitz.Rect(scaled_x, scaled_y, scaled_x + scaled_sig_width, scaled_y + scaled_sig_height)
            
            page.insert_image(sig_rect, filename=signature_path)
            
            output_filename = f"firmado_{secure_filename(document_file.filename)}"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            pdf_document.save(output_path)
            pdf_document.close()

        elif document_file.mimetype.startswith('image/'):
            doc_image = Image.open(io.BytesIO(doc_stream)).convert("RGBA")
            signature_image = Image.open(signature_path).convert("RGBA")

            scale_factor = doc_image.width / 800
            scaled_sig_width = int(sig_width * scale_factor)
            aspect_ratio = signature_image.height / signature_image.width
            scaled_sig_height = int(scaled_sig_width * aspect_ratio)
            signature_image = signature_image.resize((scaled_sig_width, scaled_sig_height))
            
            scaled_x = int(pos_x * scale_factor)
            scaled_y = int(pos_y * scale_factor)

            doc_image.paste(signature_image, (scaled_x, scaled_y), signature_image)

            output_filename = f"firmado_{secure_filename(document_file.filename)}"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            doc_image.save(output_path, "PNG")

        else:
            return jsonify({'error': 'Tipo de archivo no soportado para firma visual.'}), 415

        download_url = url_for('serve_upload', filename=output_filename, _external=True)
        return jsonify({
            'message': '¡Documento firmado con éxito!',
            'file_path': download_url
        })

    except Exception as e:
        print(f"ERROR DETALLADO AL FIRMAR: {e}")
        return jsonify({'error': f'Error al procesar el documento: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
