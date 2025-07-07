// static/js/signature.js - Solución al problema de guardar firma para reutilizar.

document.addEventListener('DOMContentLoaded', () => {

    // --- VARIABLES Y ELEMENTOS ---
    const canvas = document.getElementById('signature-canvas');
    const clearButton = document.getElementById('clear-btn');
    const prepareCanvasButton = document.getElementById('prepare-canvas-btn'); // Prepara la firma del canvas
    const fileInput = document.getElementById('file-input'); // Input para subir archivo de firma
    const finalUploadButton = document.getElementById('final-upload-btn'); // Botón para subir DOCUMENTO Y FIRMA
    const statusText = document.getElementById('status-text');
    const downloadButton = document.getElementById('download-btn');
    const documentInput = document.getElementById('document-input'); // Input para el documento a firmar

    const saveSignatureBtn = document.getElementById('save-signature-btn'); // NUEVO/MODIFICADO: Botón para guardar solo la firma

    // Verificación de elementos
    if (!canvas || !clearButton || !prepareCanvasButton || !fileInput || !finalUploadButton || !statusText || !documentInput || !saveSignatureBtn) { 
        console.error("Error crítico: Uno o más elementos del HTML no se encontraron. Revisa los IDs.");
        return;
    }
    
    let signatureToUpload = null; // Almacena el Blob de la firma actual (canvas o archivo)
    let lastSavedSignatureUrl = null; // NUEVO: Almacena la URL de la última firma GUARDADA
    
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';
    let drawing = false;

    // --- LÓGICA DE DIBUJO (Sin cambios) ---
    function startPosition(e) { drawing = true; draw(e); }
    function endPosition() { drawing = false; ctx.beginPath(); }
    function draw(e) {
        if (!drawing) return;
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX || e.touches[0].clientX) - rect.left;
        const y = (e.clientY || e.touches[0].clientY) - rect.top;
        ctx.lineTo(x, y); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x, y);
    }
    canvas.addEventListener('mousedown', startPosition);
    canvas.addEventListener('mouseup', endPosition);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseleave', endPosition);
    canvas.addEventListener('touchstart', startPosition);
    canvas.addEventListener('touchend', endPosition);
    canvas.addEventListener('touchmove', draw);

    // --- LÓGICA DE LOS BOTONES DE ACCIÓN ---
    clearButton.addEventListener('click', () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        signatureToUpload = null; // Limpiar la firma preparada
        statusText.textContent = 'Estado: Lienzo limpio.';
        statusText.classList.remove('success', 'error');
    });

    // prepareCanvasButton: Solo prepara el blob de la firma dibujada del canvas
    prepareCanvasButton.addEventListener('click', () => {
        const blank = document.createElement('canvas');
        blank.width = canvas.width; blank.height = canvas.height;
        if (canvas.toDataURL() === blank.toDataURL()) {
            statusText.textContent = 'Estado: Por favor, dibuja una firma antes de preparar.';
            statusText.classList.remove('success');
            statusText.classList.add('error');
            signatureToUpload = null;
            return;
        }

        const dataUrl = canvas.toDataURL('image/png');
        fetch(dataUrl).then(res => res.blob()).then(blob => {
            signatureToUpload = blob;
            statusText.textContent = 'Estado: Firma dibujada lista para guardar o subir.';
            statusText.classList.remove('error');
            statusText.classList.add('success');
            console.log("Firma del canvas preparada.", signatureToUpload);
            fileInput.value = ''; // Asegurar que no haya un archivo seleccionado si se usa el canvas
        });
    });

    if (downloadButton) {
        downloadButton.addEventListener('click', () => {
            const blank = document.createElement('canvas');
            blank.width = canvas.width; blank.height = canvas.height;
            if (canvas.toDataURL() === blank.toDataURL()) {
                alert("Por favor, dibuja una firma antes de descargar."); return;
            }
            const signatureDataUrl = canvas.toDataURL('image/png');
            const link = document.createElement('a');
            link.href = signatureDataUrl;
            link.download = `firma-descargada-${Date.now()}.png`;
            link.click();
        });
    }

    // fileInput: Prepara el blob de la firma seleccionada de un archivo
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            signatureToUpload = fileInput.files[0];
            statusText.textContent = `Estado: Listo para guardar o subir el archivo '${signatureToUpload.name}'.`;
            statusText.classList.remove('error');
            statusText.classList.add('success');
            console.log("Archivo de firma preparado.", signatureToUpload);
            ctx.clearRect(0, 0, canvas.width, canvas.height); // Limpiar el canvas si se carga un archivo
        } else {
            signatureToUpload = null;
            statusText.textContent = 'Estado: Ningún archivo de firma seleccionado.';
            statusText.classList.remove('success');
            statusText.classList.add('error');
        }
    });

    // --- LÓGICA DE GUARDAR FIRMA PARA REUTILIZACIÓN ---
    saveSignatureBtn.addEventListener('click', () => {
        if (!signatureToUpload) {
            statusText.textContent = 'Estado: Primero dibuja o selecciona un archivo de firma para guardar.';
            statusText.classList.remove('success');
            statusText.classList.add('error');
            return;
        }

        const formData = new FormData();
        const filename = signatureToUpload.name || `firma_dibujada_${Date.now()}.png`;
        formData.append('signature_file', signatureToUpload, filename);
        
        statusText.textContent = 'Guardando firma para reutilización...';
        statusText.classList.remove('success', 'error');

        fetch('/upload_signature', { // Esta es la ruta en app.py que guarda la firma para reutilización
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) { throw new Error(`Error del servidor: ${response.statusText}`); }
            return response.json();
        })
        .then(data => {
            if(data.message) {
                statusText.textContent = `¡Éxito! ${data.message}`;
                statusText.classList.remove('error');
                statusText.classList.add('success');
                lastSavedSignatureUrl = data.signature_url; // Almacena la URL de la firma guardada
                console.log("URL de firma guardada:", lastSavedSignatureUrl);
                // Opcional: limpiar signatureToUpload si se considera que ya fue "procesada"
                // signatureToUpload = null; 
                // ctx.clearRect(0, 0, canvas.width, canvas.height); 
                // fileInput.value = ''; 
            } else if (data.error) {
                statusText.textContent = `Error: ${data.error}`;
                statusText.classList.remove('success');
                statusText.classList.add('error');
            }
        })
        .catch(error => {
            console.error('Error al guardar la firma:', error);
            statusText.textContent = `Estado: Error al guardar la firma. ${error.message}`;
            statusText.classList.remove('success');
            statusText.classList.add('error');
        });
    });

    // --- LÓGICA DEL BOTÓN FINAL DE SUBIDA (documento + firma temporal/recién preparada) ---
    finalUploadButton.addEventListener('click', () => {
        // Validación de documento
        if (documentInput.files.length === 0) {
            statusText.textContent = 'Estado: Paso 1: Por favor, selecciona un documento para subir.';
            statusText.classList.remove('success');
            statusText.classList.add('error');
            return;
        }

        const documentFile = documentInput.files[0];
        // *** CORRECCIÓN: Asegurarse de que el archivo existe antes de acceder a sus propiedades ***
        if (!documentFile) {
            statusText.textContent = 'Estado: No se pudo acceder al archivo del documento. Intenta de nuevo.';
            statusText.classList.remove('success');
            statusText.classList.add('error');
            return;
        }
        // **************************************************************************************

        // Validación de firma: Se requiere una firma preparada (del canvas o de archivo)
        if (!signatureToUpload) {
            statusText.textContent = 'Estado: Paso 2: Por favor, dibuja o selecciona un archivo de firma.';
            statusText.classList.remove('success');
            statusText.classList.add('error');
            return;
        }

        const formData = new FormData();
        formData.append('document_file', documentFile);
        formData.append('signature_file', signatureToUpload, signatureToUpload.name || `firma-canvas-${Date.now()}.png`);
        
        statusText.textContent = 'Subiendo documento y firma asociada...';
        statusText.classList.remove('success', 'error');
        console.log("Enviando al backend:", { documentFile: documentFile.name, signatureFile: signatureToUpload.name || 'firma_canvas' });

        fetch('/upload_document', { // Esta ruta en app.py solo guarda los archivos, no los combina visualmente
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) { throw new Error(`Error del servidor: ${response.statusText}`); }
            return response.json();
        })
        .then(data => {
            if(data.message) {
                statusText.textContent = `¡Subida completada! ${data.message}. Ahora ve al Dashboard para firmar visualmente.`;
                statusText.classList.remove('error');
                statusText.classList.add('success');
                // Limpiar inputs después de subir
                signatureToUpload = null;
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                fileInput.value = '';
                documentInput.value = ''; 
                // No limpiamos lastSavedSignatureUrl, ya que la firma podría haber sido guardada previamente.
            } else if (data.error) {
                statusText.textContent = `Error: ${data.error}`;
                statusText.classList.remove('success');
                statusText.classList.add('error');
            }
        })
        .catch(error => {
            console.error('Error al subir:', error);
            statusText.textContent = `Estado: Error al subir. Intenta de nuevo. ${error.message}`;
            statusText.classList.remove('success');
            statusText.classList.add('error');
        });
    });
});
