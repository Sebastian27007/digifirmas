// signature.js - Versión Final con Asociación de Documentos

document.addEventListener('DOMContentLoaded', () => {

    // --- VARIABLES Y ELEMENTOS ---
    const canvas = document.getElementById('signature-canvas');
    const clearButton = document.getElementById('clear-btn');
    const prepareCanvasButton = document.getElementById('prepare-canvas-btn');
    const fileInput = document.getElementById('file-input');
    const finalUploadButton = document.getElementById('final-upload-btn');
    const statusText = document.getElementById('status-text');
    const downloadButton = document.getElementById('download-btn');
    const documentInput = document.getElementById('document-input'); // <-- NUEVO: El input para el documento

    // Esta comprobación ahora incluye el nuevo input del documento.
    if (!canvas || !clearButton || !prepareCanvasButton || !fileInput || !finalUploadButton || !statusText || !documentInput) { // <-- NUEVO: !documentInput
        console.error("Error crítico: Uno o más elementos del HTML no se encontraron. Revisa los IDs.");
        return;
    }
    
    let signatureToUpload = null;
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

    // --- LÓGICA DE LOS BOTONES DE ACCIÓN (Sin cambios en los existentes) ---
    clearButton.addEventListener('click', () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    });

    prepareCanvasButton.addEventListener('click', () => {
        const dataUrl = canvas.toDataURL('image/png');
        fetch(dataUrl).then(res => res.blob()).then(blob => {
            signatureToUpload = blob;
            statusText.textContent = 'Estado: Lista para subir la firma dibujada.';
            console.log("Firma del canvas preparada.", signatureToUpload);
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

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            signatureToUpload = fileInput.files[0];
            statusText.textContent = `Estado: Listo para subir el archivo '${signatureToUpload.name}'.`;
            console.log("Archivo de firma preparado.", signatureToUpload);
        }
    });

    // --- LÓGICA DEL BOTÓN FINAL DE SUBIDA (Modificada) ---
    finalUploadButton.addEventListener('click', () => {
        // <-- NUEVO: Primero validamos que se haya seleccionado un documento.
        if (documentInput.files.length === 0) {
            alert('Paso 1: Por favor, selecciona un documento para firmar.');
            return;
        }

        // Después validamos la firma.
        if (!signatureToUpload) {
            alert('Paso 2: Por favor, dibuja o selecciona un archivo de firma.');
            return;
        }

        // <-- NUEVO: Obtenemos el archivo del documento.
        const documentFile = documentInput.files[0];

        const formData = new FormData();
        // <-- NUEVO: Añadimos ambos archivos al mismo FormData.
        formData.append('document_file', documentFile);
        formData.append('signature_file', signatureToUpload, signatureToUpload.name || `firma-canvas-${Date.now()}.png`);
        
        statusText.textContent = 'Subiendo documento y firma...';
        console.log("Enviando al backend:", { documentFile, signatureFile: signatureToUpload });

        fetch('/upload_document', {
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) { throw new Error(`Error del servidor: ${response.statusText}`); }
            return response.json();
        })
        .then(data => {
            alert(`¡Éxito! Archivo subido: ${data.file_path}`);
            statusText.textContent = '¡Subida completada! Listo para un nuevo documento.';
            signatureToUpload = null;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            fileInput.value = '';
            documentInput.value = ''; // <-- NUEVO: También limpiamos el input del documento.
        })
        .catch(error => {
            console.error('Error al subir:', error);
            alert(`Ocurrió un error al subir los archivos. ${error.message}`);
            statusText.textContent = `Estado: Error al subir. Intenta de nuevo.`;
        });
    });

});