document.addEventListener('DOMContentLoaded', () => {

    // --- VARIABLES Y ELEMENTOS ---
    const canvas = document.getElementById('signature-canvas');
    const clearButton = document.getElementById('clear-btn');
    const prepareCanvasButton = document.getElementById('prepare-canvas-btn');
    const fileInput = document.getElementById('file-input');
    const finalUploadButton = document.getElementById('final-upload-btn');
    const statusText = document.getElementById('status-text');
    const downloadButton = document.getElementById('download-btn');

    // Esta comprobación es clave. Si alguno de los elementos principales no existe, detenemos para evitar errores.
    if (!canvas || !clearButton || !prepareCanvasButton || !fileInput || !finalUploadButton || !statusText) {
        console.error("Error crítico: Uno o más elementos del HTML no se encontraron. Revisa los IDs.");
        return;
    }
    
    // Esta es nuestra "memoria". Guardará la firma lista para ser subida.
    let signatureToUpload = null;

    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';
    let drawing = false;

    // --- LÓGICA DE DIBUJO ---
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
    // Este botón limpia el canvas, permitiendo al usuario empezar de nuevo.
    clearButton.addEventListener('click', () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    });

    // Este botón prepara la firma dibujada en el canvas para ser subida.
    prepareCanvasButton.addEventListener('click', () => {
        const dataUrl = canvas.toDataURL('image/png');
        fetch(dataUrl)
            .then(res => res.blob())
            .then(blob => {
                signatureToUpload = blob;
                statusText.textContent = 'Estado: Lista para subir la firma dibujada.';
                console.log("Firma del canvas preparada.", signatureToUpload);
            });
    });

    if (downloadButton) {
    downloadButton.addEventListener('click', () => {
        console.log("Botón Descargar presionado.");

        // Verifica si el canvas está vacío para no descargar una imagen en blanco
        const blank = document.createElement('canvas');
        blank.width = canvas.width;
        blank.height = canvas.height;
        if (canvas.toDataURL() === blank.toDataURL()) {
            alert("Por favor, dibuja una firma antes de descargar.");
            return;
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
            console.log("Archivo seleccionado preparado.", signatureToUpload);
        }
    });

    // Este botón sube la firma, ya sea del canvas o del archivo seleccionado.
    finalUploadButton.addEventListener('click', () => {
        if (!signatureToUpload) {
            alert('Por favor, primero dibuja una firma y presiona "Usar Firma Dibujada", o selecciona un archivo.');
            return;
        }

        const formData = new FormData();
        formData.append('signature_file', signatureToUpload, signatureToUpload.name || `firma-canvas-${Date.now()}.png`);
        
        statusText.textContent = 'Subiendo...';
        console.log("Enviando al backend...", signatureToUpload);

        fetch('/upload_signature', {
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) { throw new Error(`Error del servidor: ${response.statusText}`); }
            return response.json();
        })
        .then(data => {
            alert(`¡Éxito! Firma subida. Archivo: ${data.file_path}`);
            statusText.textContent = 'Estado: ¡Subida completada! Esperando nueva firma.';
            signatureToUpload = null;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            fileInput.value = '';
        })
        .catch(error => {
            console.error('Error al subir:', error);
            alert(`Ocurrió un error al subir la firma. ${error.message}`);
            statusText.textContent = `Estado: Error al subir. Intenta de nuevo.`;
        });
    });

}); 