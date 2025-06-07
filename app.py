import os
import base64
from flask import Flask, render_template, request

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save_signature', methods=['POST'])
def save_signature():
    data_url = request.form['imageData']
    header, encoded = data_url.split(",", 1)
    data = base64.b64decode(encoded)

    filename = os.path.join(UPLOAD_FOLDER, 'firma.png')
    with open(filename, 'wb') as f:
        f.write(data)

    return 'Firma guardada correctamente.'

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

@app.route('/upload_signature', methods=['POST'])
def upload_signature():
    file = request.files.get('signatureImage')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return 'Imagen subida correctamente.'
    return 'No se seleccionó ningún archivo.'
