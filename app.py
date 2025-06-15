import os
import uuid
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- RUTAS ---

# Ruta para mostrar la página principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para recibir y asociar el documento y la firma
@app.route('/upload_document', methods=['POST'])
def upload_document():
    # Validaciones de seguridad
    if 'document_file' not in request.files or 'signature_file' not in request.files:
        return jsonify({'error': 'Petición inválida, faltan archivos'}), 400

    document = request.files['document_file']
    signature = request.files['signature_file']

    if document.filename == '' or signature.filename == '':
        return jsonify({'error': 'No se seleccionaron todos los archivos necesarios'}), 400

    # Lógica de asociación y guardado
    if document and signature:
        secure_doc_name = secure_filename(document.filename)
        secure_sig_name = secure_filename(signature.filename)
        unique_id = str(uuid.uuid4())
        
        doc_filename = f"{unique_id}_{secure_doc_name}"
        sig_filename = f"{unique_id}_{secure_sig_name}"

        doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
        sig_path = os.path.join(app.config['UPLOAD_FOLDER'], sig_filename)
        
        document.save(doc_path)
        signature.save(sig_path)

        # Devolver respuesta exitosa al frontend
        return jsonify({
            'message': 'Documento y firma subidos y asociados con éxito',
            'file_path': doc_filename 
        }), 200

    return jsonify({'error': 'Ocurrió un error inesperado'}), 500

# --- INICIAR EL SERVIDOR ---
if __name__ == '__main__':
    app.run(debug=True)