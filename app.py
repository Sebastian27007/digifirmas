import os
import uuid
import base64 # Importado desde main, puede ser útil
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename

# Imports adicionales para el manejo de PDFs e imágenes
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import io

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

# --- FUNCIONES AUXILIARES PARA MANEJO DE PDFs ---

def encontrar_archivos_asociados(unique_id, username):
    """
    Esta función es como un detective que busca todos los archivos que pertenecen 
    a un mismo documento-firma usando el ID único que creamos.
    
    Es como buscar piezas de un rompecabezas que tienen el mismo color de borde.
    """
    archivos_encontrados = {
        'documento': None,
        'firma': None
    }
    
    # Recorremos todos los archivos en la carpeta uploads
    for archivo in os.listdir(app.config['UPLOAD_FOLDER']):
        # Verificamos si el archivo pertenece a este usuario y tiene este ID único
        if archivo.startswith(f"{username}_{unique_id}_"):
            # Separamos el nombre para identificar qué tipo de archivo es
            partes = archivo.split('_', 2)  # [username, unique_id, filename_original]
            
            if len(partes) >= 3:
                nombre_original = partes[2].lower()
                ruta_completa = os.path.join(app.config['UPLOAD_FOLDER'], archivo)
                
                # Identificamos si es un documento o una firma por su extensión
                if nombre_original.endswith(('.pdf', '.doc', '.docx', '.txt')):
                    archivos_encontrados['documento'] = ruta_completa
                elif nombre_original.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    archivos_encontrados['firma'] = ruta_completa
    
    return archivos_encontrados

def crear_pdf_con_firma(documento_path, firma_path, username, unique_id):
    """
    Esta función es como un artista que toma un lienzo (documento) y una firma,
    y los combina en una obra de arte final (PDF firmado).
    
    Es como pegar una calcomanía en el lugar exacto de un documento.
    """
    try:
        # Nombre del archivo final - será fácil de identificar
        nombre_pdf_final = f"{username}_{unique_id}_documento_firmado.pdf"
        ruta_pdf_final = os.path.join(app.config['UPLOAD_FOLDER'], nombre_pdf_final)
        
        # Preparamos la imagen de la firma
        # Esto es como recortar la firma para que tenga el tamaño perfecto
        firma_img = Image.open(firma_path)
        
        # Redimensionamos la firma para que no sea muy grande ni muy pequeña
        # Es como ajustar el tamaño de una calcomanía antes de pegarla
        ancho_firma = 150  # píxeles
        alto_firma = 75    # píxeles
        firma_img = firma_img.resize((ancho_firma, alto_firma), Image.Resampling.LANCZOS)
        
        # Convertimos la firma a formato que PDF puede entender
        firma_buffer = io.BytesIO()
        if firma_img.mode != 'RGB':
            firma_img = firma_img.convert('RGB')
        firma_img.save(firma_buffer, format='PNG')
        firma_buffer.seek(0)
        
        # Ahora trabajamos con el documento original
        extension_documento = os.path.splitext(documento_path)[1].lower()
        
        if extension_documento == '.pdf':
            # Si el documento original es PDF, lo usamos directamente
            # Es como tener una hoja ya impresa y agregarle la firma
            return agregar_firma_a_pdf_existente(documento_path, firma_buffer, ruta_pdf_final)
        else:
            # Si el documento es una imagen, primero lo convertimos a PDF
            # Es como escanear una hoja de papel y luego agregarle la firma
            return crear_pdf_desde_imagen_con_firma(documento_path, firma_buffer, ruta_pdf_final)
            
    except Exception as e:
        print(f"Error al crear PDF con firma: {str(e)}")
        return None

def agregar_firma_a_pdf_existente(documento_pdf_path, firma_buffer, ruta_salida):
    """
    Esta función toma un PDF que ya existe y le agrega la firma.
    Es como usar un sello en un documento oficial.
    """
    try:
        # Leemos el PDF original
        lector_pdf = PdfReader(documento_pdf_path)
        escritor_pdf = PdfWriter()
        
        # Creamos una página temporal solo para la firma
        # Esto es como crear una hoja transparente con solo la firma
        buffer_pagina_firma = io.BytesIO()
        c = canvas.Canvas(buffer_pagina_firma, pagesize=letter)
        
        # Posicionamos la firma (abajo a la derecha por defecto)
        # Puedes cambiar estos números para mover la firma
        posicion_x = 400  # Hacia la derecha
        posicion_y = 50   # Hacia arriba desde abajo
        
        # Dibujamos la firma en la posición elegida
        c.drawImage(firma_buffer, posicion_x, posicion_y, width=150, height=75)
        c.save()
        
        # Convertimos nuestra página temporal en un PDF real
        buffer_pagina_firma.seek(0)
        pdf_firma = PdfReader(buffer_pagina_firma)
        
        # Ahora combinamos cada página del documento original con la firma
        # Es como poner un papel transparente con la firma sobre cada página
        for num_pagina, pagina in enumerate(lector_pdf.pages):
            if num_pagina == len(lector_pdf.pages) - 1:  # Solo en la última página
                # Superponemos la firma en la última página
                pagina.merge_page(pdf_firma.pages[0])
            escritor_pdf.add_page(pagina)
        
        # Guardamos el resultado final
        with open(ruta_salida, 'wb') as archivo_salida:
            escritor_pdf.write(archivo_salida)
        
        return ruta_salida
        
    except Exception as e:
        print(f"Error al agregar firma a PDF existente: {str(e)}")
        return None

def crear_pdf_desde_imagen_con_firma(imagen_path, firma_buffer, ruta_salida):
    """
    Esta función convierte una imagen en PDF y luego le agrega la firma.
    Es como escanear una foto y después firmarla digitalmente.
    """
    try:
        # Abrimos la imagen del documento
        imagen_documento = Image.open(imagen_path)
        
        # La convertimos a RGB si no lo está ya (necesario para PDF)
        if imagen_documento.mode != 'RGB':
            imagen_documento = imagen_documento.convert('RGB')
        
        # Creamos un nuevo PDF
        c = canvas.Canvas(ruta_salida, pagesize=letter)
        ancho_pagina, alto_pagina = letter
        
        # Calculamos cómo ajustar la imagen al tamaño de la página
        # Es como decidir si imprimir una foto grande en una hoja carta
        ancho_img, alto_img = imagen_documento.size
        factor_escala = min(ancho_pagina/ancho_img, alto_pagina/alto_img)
        
        nuevo_ancho = ancho_img * factor_escala
        nuevo_alto = alto_img * factor_escala
        
        # Centramos la imagen en la página
        x = (ancho_pagina - nuevo_ancho) / 2
        y = (alto_pagina - nuevo_alto) / 2
        
        # Convertimos la imagen para que el PDF la pueda usar
        buffer_imagen = io.BytesIO()
        imagen_documento.save(buffer_imagen, format='PNG')
        buffer_imagen.seek(0)
        
        # Dibujamos la imagen del documento
        c.drawImage(buffer_imagen, x, y, width=nuevo_ancho, height=nuevo_alto)
        
        # Ahora agregamos la firma encima
        # La posicionamos en la esquina inferior derecha
        firma_x = ancho_pagina - 170  # 20 píxeles del borde derecho
        firma_y = 20  # 20 píxeles del borde inferior
        
        c.drawImage(firma_buffer, firma_x, firma_y, width=150, height=75)
        
        # Guardamos el PDF final
        c.save()
        
        return ruta_salida
        
    except Exception as e:
        print(f"Error al crear PDF desde imagen con firma: {str(e)}")
        return None


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


@app.route('/generar_pdf_firmado', methods=['POST'])
def generar_pdf_firmado():
    """
    Esta ruta es como el director de orquesta que coordina todo el proceso
    de crear un documento firmado. Es el "botón mágico" que el usuario presiona
    para obtener su documento final.
    """
    
    # 1. Verificamos que el usuario tenga sesión iniciada
    if 'username' not in session:
        return jsonify({'error': 'Usuario no autenticado'}), 401
    
    try:
        # 2. Obtenemos los datos que el usuario nos envía
        data = request.get_json()
        
        if not data or 'unique_id' not in data:
            return jsonify({'error': 'ID único no proporcionado'}), 400
        
        unique_id = data['unique_id']
        username = session['username']
        
        # 3. Buscamos los archivos que van juntos (documento y firma)
        # Es como buscar las dos piezas de un rompecabezas que encajan
        archivos = encontrar_archivos_asociados(unique_id, username)
        
        if not archivos['documento'] or not archivos['firma']:
            return jsonify({
                'error': 'No se encontraron todos los archivos necesarios',
                'encontrados': archivos
            }), 404
        
        # 4. Ahora viene la magia: combinamos documento y firma
        print(f"Creando PDF firmado para usuario: {username}, ID: {unique_id}")
        print(f"Documento: {archivos['documento']}")
        print(f"Firma: {archivos['firma']}")
        
        ruta_pdf_final = crear_pdf_con_firma(
            archivos['documento'], 
            archivos['firma'], 
            username, 
            unique_id
        )
        
        if ruta_pdf_final:
            # 5. ¡Éxito! Devolvemos la información del archivo creado
            nombre_archivo = os.path.basename(ruta_pdf_final)
            return jsonify({
                'success': True,
                'message': '¡PDF firmado creado exitosamente!',
                'archivo': nombre_archivo,
                'ruta_descarga': f'/descargar/{nombre_archivo}'
            }), 200
        else:
            return jsonify({
                'error': 'Error al crear el PDF firmado'
            }), 500
            
    except Exception as e:
        print(f"Error en generar_pdf_firmado: {str(e)}")
        return jsonify({
            'error': f'Error interno del servidor: {str(e)}'
        }), 500

@app.route('/descargar/<filename>')
def descargar_archivo(filename):
    """
    Esta ruta permite a los usuarios descargar sus documentos firmados.
    Es como el mostrador de entrega en una tienda - aquí recogen su pedido.
    """
    
    # Verificamos que el usuario tenga sesión iniciada
    if 'username' not in session:
        flash("Por favor, inicia sesión para descargar archivos.")
        return redirect(url_for('login'))
    
    try:
        # Verificamos que el archivo le pertenezca al usuario actual
        # Esto es importante para la seguridad - no queremos que alguien 
        # descargue archivos de otros usuarios
        username = session['username']
        
        if not filename.startswith(f"{username}_"):
            flash("No tienes permiso para descargar este archivo.")
            return redirect(url_for('index'))
        
        # Verificamos que el archivo exista
        ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(ruta_archivo):
            flash("El archivo solicitado no existe.")
            return redirect(url_for('index'))
        
        # Enviamos el archivo al usuario
        return send_file(
            ruta_archivo, 
            as_attachment=True, 
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error al descargar archivo: {str(e)}")
        flash("Error al descargar el archivo.")
        return redirect(url_for('index'))

# También agregar esta ruta para listar los documentos del usuario
@app.route('/mis_documentos')
def mis_documentos():
    """
    Esta ruta muestra al usuario todos sus documentos firmados.
    Es como un archivero personal donde puede ver todo lo que ha creado.
    """
    
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    documentos_firmados = []
    
    try:
        # Buscamos todos los PDFs firmados del usuario
        for archivo in os.listdir(app.config['UPLOAD_FOLDER']):
            if archivo.startswith(f"{username}_") and archivo.endswith('_documento_firmado.pdf'):
                # Extraemos información útil del nombre del archivo
                partes = archivo.split('_')
                if len(partes) >= 3:
                    unique_id = partes[1]
                    fecha_creacion = os.path.getctime(
                        os.path.join(app.config['UPLOAD_FOLDER'], archivo)
                    )
                    
                    documentos_firmados.append({
                        'nombre': archivo,
                        'id_unico': unique_id,
                        'fecha': fecha_creacion,
                        'ruta_descarga': f'/descargar/{archivo}'
                    })
        
        # Ordenamos por fecha de creación (más recientes primero)
        documentos_firmados.sort(key=lambda x: x['fecha'], reverse=True)
        
    except Exception as e:
        print(f"Error al listar documentos: {str(e)}")
        flash("Error al cargar la lista de documentos.")
    
    return render_template('dashboard.html', 
                         username=username, 
                         documentos=documentos_firmados)



# --- INICIAR EL SERVIDOR ---
if __name__ == '__main__':
    app.run(debug=True)