import os
import uuid
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import io
import fitz
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'secreto_super_seguro')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SIGNATURES_SUBFOLDER'] = os.path.join(UPLOAD_FOLDER, 'firmas')
app.config['SIGNED_DOCUMENTS_SUBFOLDER'] = os.path.join(UPLOAD_FOLDER, 'documentos_firmados')

os.makedirs(app.config['SIGNATURES_SUBFOLDER'], exist_ok=True)
os.makedirs(app.config['SIGNED_DOCUMENTS_SUBFOLDER'], exist_ok=True)

USERS_DB_FILE = 'users_db.json'

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lbfglpcrjpmfzqsstpvq.supabase.co")
# Se actualizó la clave Supabase con la nueva clave proporcionada.
# ADVERTENCIA: Para operaciones de escritura en el backend, la service_role key es más segura.
# Si usas la anon public key, asegúrate de que tus políticas RLS en Supabase estén configuradas
# para permitir las operaciones de inserción y selección para usuarios autenticados.
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_9Z_xJ6AOutVeqF4TGehMyw_c6O9uxW9")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_users():
    if os.path.exists(USERS_DB_FILE):
        with open(USERS_DB_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Advertencia: El archivo {USERS_DB_FILE} está vacío o corrupto. Se iniciará con un diccionario vacío.")
                return {}
    return {}

def save_users(users_data):
    with open(USERS_DB_FILE, 'w') as f:
        json.dump(users_data, f, indent=4)

usuarios = load_users()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        global usuarios
        usuarios = load_users()

        if username in usuarios:
            flash("El nombre de usuario ya existe localmente.")
            return render_template('register.html')
        
        for user_data in usuarios.values():
            if user_data.get('email') == email:
                flash("El correo electrónico ya está registrado localmente.")
                return render_template('register.html')

        try:
            # 1. Intentar registrar el usuario en Supabase Auth
            user_response = supabase.auth.sign_up({"email": email, "password": password})
            user = user_response.user
            error = user_response.session # Supabase devuelve el error aquí si no hay user

            if user:
                print(f"Usuario registrado en Supabase Auth: {user.id}")

                # 2. Guardar el usuario en la base de datos JSON local
                hashed_password = generate_password_hash(password)
                usuarios[username] = {
                    'password': hashed_password,
                    'email': email,
                    'firmas_guardadas': [],
                    'supabase_id': user.id
                }
                save_users(usuarios)
                print(f"Usuario guardado localmente: {username}")

                # 3. Insertar el perfil del usuario en la tabla 'usuarios' de Supabase
                # Asegúrate de que la tabla 'public.usuarios' exista en Supabase
                # con columnas 'id', 'username', 'email' y 'created_at'.
                # La columna 'id' debe ser el user.id de Supabase Auth.
                try:
                    response_db = supabase.from_('usuarios').insert({
                        'id': user.id,
                        'username': username,
                        'email': email
                    }).execute()
                    data = response_db.data
                    count = response_db.count
                    print(f"Perfil de usuario insertado en tabla 'usuarios' de Supabase: {data}")
                except Exception as db_error:
                    print(f"Error al insertar perfil en tabla 'usuarios' de Supabase: {db_error}")
                    flash(f"Registro exitoso en autenticación, pero error al guardar perfil: {str(db_error)}")
                    # Considera revertir el registro de Supabase Auth si la inserción del perfil es crítica
                    # o simplemente registrar el error y continuar.

                flash("Registro exitoso. Ahora inicia sesión.")
                return redirect(url_for('login'))
            else:
                print(f"Error de Supabase Auth: {error.message if error else 'Error desconocido'}")
                flash(f"Error al registrar en Supabase: {error.message if error else 'Ocurrió un error desconocido durante el registro.'}")
        except Exception as e:
            print(f"Excepción inesperada durante el registro: {e}")
            flash(f"Error inesperado durante el registro: {str(e)}")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_username = request.form['email_or_username']
        password = request.form['password']

        global usuarios
        usuarios = load_users()

        try:
            user_response = supabase.auth.sign_in_with_password({"email": email_or_username, "password": password})
            user = user_response.user
            error = user_response.session

            if user:
                local_user_found = None
                local_username = None
                # Obtener el username de la tabla 'usuarios' de Supabase
                try:
                    response_user_data = supabase.from_('usuarios').select('username').eq('id', user.id).single().execute()
                    user_data_from_db = response_user_data.data
                    if user_data_from_db:
                        local_username = user_data_from_db['username']
                except Exception as db_error:
                    print(f"Error al obtener username de Supabase: {db_error}")
                    local_username = email_or_username # Fallback si no se encuentra en la tabla de usuarios

                # Buscar usuario localmente (por compatibilidad)
                for uname, udata in usuarios.items():
                    if udata.get('supabase_id') == user.id or udata.get('email') == email_or_username:
                        local_user_found = udata
                        if not local_username: # Si no lo obtuvimos de Supabase, usar el local
                            local_username = uname
                        break
                
                if local_user_found:
                    session['user_id'] = user.id
                    session['username'] = local_username
                    flash(f"Bienvenido, {local_username}!")
                    return redirect(url_for('index'))
                else:
                    flash("Usuario autenticado en Supabase, pero no encontrado localmente. Contacta al administrador.")
                    supabase.auth.sign_out()
                    return render_template('login.html')
            else:
                flash(f"Credenciales incorrectas en Supabase: {error.message if error else 'Error desconocido'}")

        except Exception as e:
            print(f"Error inesperado durante el inicio de sesión con Supabase: {str(e)}")
            user_data = usuarios.get(email_or_username)
            if user_data and check_password_hash(user_data['password'], password):
                session['username'] = email_or_username
                session['user_id'] = user_data.get('supabase_id')
                flash(f"Bienvenido, {email_or_username} (autenticación local)!")
                return redirect(url_for('index'))
            else:
                flash("Credenciales incorrectas (local o Supabase).")

    return render_template('login.html')

@app.route('/logout')
def logout():
    try:
        supabase.auth.sign_out()
        session.pop('username', None)
        session.pop('user_id', None)
        flash("Sesión cerrada correctamente.")
    except Exception as e:
        flash(f"Error al cerrar sesión de Supabase: {str(e)}")
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session and 'username' not in session:
        flash("Por favor, inicia sesión para acceder a esta página.")
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username', 'Usuario'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session and 'username' not in session:
        flash("Por favor, inicia sesión para acceder al dashboard.")
        return redirect(url_for('login'))
    
    username = session.get('username', 'Usuario')
    user_id = session.get('user_id')

    global usuarios
    usuarios = load_users()

    firmas_urls = []
    if username in usuarios and 'firmas_guardadas' in usuarios[username]:
        for filename in usuarios[username]['firmas_guardadas']:
            firmas_urls.append(url_for('uploaded_file', filename=f'firmas/{filename}'))
    
    # Aquí podrías también cargar firmas desde Supabase si las tuvieras allí
    if user_id:
        try:
            response_signatures = supabase.from_('user_signatures').select('filename').eq('supabase_user_id', user_id).execute()
            signatures_from_db = response_signatures.data
            if signatures_from_db:
                for item in signatures_from_db:
                    firmas_urls.append(url_for('uploaded_file', filename=f'firmas/{item["filename"]}'))
        except Exception as e:
            print(f"Error al cargar firmas desde Supabase: {e}")

    return render_template('dashboard.html', username=username, firmas=firmas_urls)

@app.route('/upload_signature', methods=['POST'])
def upload_signature():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401

    if 'signature_file' not in request.files:
        return jsonify({'error': 'No se encontró el archivo de firma'}), 400

    signature_file = request.files['signature_file']
    if signature_file.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo de firma'}), 400

    username = session.get('username', 'unknown_user')
    user_id = session['user_id']
    unique_sig_id = str(uuid.uuid4().hex)[:12]
    original_filename = secure_filename(signature_file.filename) if signature_file.filename else 'firma_dibujada.png'
    sig_filename = f"{username}_{unique_sig_id}_{original_filename}"
    sig_path = os.path.join(app.config['SIGNATURES_SUBFOLDER'], sig_filename)

    try:
        signature_file.save(sig_path)
        
        global usuarios
        usuarios = load_users()
        if username in usuarios:
            if 'firmas_guardadas' not in usuarios[username]:
                usuarios[username]['firmas_guardadas'] = []
            usuarios[username]['firmas_guardadas'].append(sig_filename)
            save_users(usuarios)

        response_insert_sig = supabase.from_('user_signatures').insert({
            'supabase_user_id': user_id,
            'filename': sig_filename,
            'local_filepath': sig_path
        }).execute()
        data = response_insert_sig.data
        count = response_insert_sig.count

        if data:
            return jsonify({
                'message': 'Firma guardada con éxito para reutilización (local y Supabase)',
                'signature_url': url_for('uploaded_file', filename=f'firmas/{sig_filename}')
            }), 200
        else:
            return jsonify({'error': f'Firma guardada localmente, pero no se pudo registrar en Supabase: {count}'}), 500

    except Exception as e:
        print(f"Error al guardar la firma (local o Supabase): {e}")
        return jsonify({'error': f'Error al guardar la firma: {str(e)}'}), 500

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
    unique_id = str(uuid.uuid4().hex)[:8]
    
    doc_filename = f"{username}_{unique_id}_doc_{secure_filename(document.filename)}"
    doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
    document.save(doc_path)

    sig_filename = f"{username}_{unique_id}_sig_{secure_filename(signature.filename or 'firma_dibujada.png')}"
    sig_path = os.path.join(app.config['UPLOAD_FOLDER'], sig_filename)
    signature.save(sig_path)

    return jsonify({
        'message': 'Documento y firma subidos con éxito. Puedes firmar visualmente documentos en el Dashboard.',
        'document_path': url_for('uploaded_file', filename=doc_filename),
        'signature_path': url_for('uploaded_file', filename=sig_filename)
    }), 200

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
                rect_x1 = rect_x0 + signature_width
                rect_y1 = rect_y0 + signature_height
                
                page_rect = page.rect
                rect_x0 = max(0, min(rect_x0, page_rect.width - signature_width))
                rect_y0 = max(0, min(rect_y0, page_rect.height - signature_height))
                rect_x1 = rect_x0 + signature_width
                rect_y1 = rect_y0 + signature_height
                
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
    if not os.path.exists(USERS_DB_FILE):
        save_users({})
    app.run(debug=True)
