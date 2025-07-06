// signature.js - Versión Final Completa

document.addEventListener('DOMContentLoaded', () => {

    // --- VARIABLES Y ELEMENTOS ---
    const canvas = document.getElementById('signature-canvas');
    const clearButton = document.getElementById('clear-btn');
    const downloadButton = document.getElementById('download-btn');
    const prepareCanvasButton = document.getElementById('prepare-canvas-btn');
    const newSignatureNameInput = document.getElementById('new-signature-name');
    const saveNewSignatureButton = document.getElementById('save-new-signature-btn');
    const savedSignaturesList = document.getElementById('saved-signatures-list');
    const fileInput = document.getElementById('file-input');
    const documentInput = document.getElementById('document-input');
    const finalUploadButton = document.getElementById('final-upload-btn');
    const statusText = document.getElementById('status-text');

    // Comprobación de que todos los elementos existen para evitar errores
    if (!canvas || !clearButton || !downloadButton || !prepareCanvasButton || !newSignatureNameInput || !saveNewSignatureButton || !savedSignaturesList || !fileInput || !documentInput || !finalUploadButton || !statusText) {
        console.error("Error crítico: Uno o más elementos del HTML no se encontraron. Revisa los IDs en index.html.");
        return;
    }
    
    // Nuestra "memoria" para la firma que se va a subir
    let signatureToUpload = null;

    // --- LÓGICA DE DIBUJO ---
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';
    let drawing = false;

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

    // --- LÓGICA DE GESTIÓN DE FIRMAS ---

    // Función para cargar y mostrar las firmas guardadas
    // Reemplaza tu función actual con esta versión corregida

function loadSavedSignatures() {
    savedSignaturesList.innerHTML = '<p>Cargando firmas...</p>';
    fetch('/api/signatures')
        .then(res => res.ok ? res.json() : Promise.reject('Error al cargar firmas'))
        .then(signatures => {
            savedSignaturesList.innerHTML = '';
            if (signatures.length === 0) {
                savedSignaturesList.innerHTML = '<p>No tienes firmas guardadas.</p>';
            } else {
                signatures.forEach(sig => {
                    const sigElement = document.createElement('div');
                    sigElement.className = 'signature-item';
                    
                    // --- LÍNEA CORREGIDA ---
                    // Antes decía "/static" + sig.path, ahora incluye "/uploads/"
                    const imagePath = `/static/uploads/${sig.path}`; 
                    
                    sigElement.innerHTML = `<img src="${imagePath}" alt="${sig.name}" title="${sig.name}"><span>${sig.name}</span>`;
                    
                    sigElement.addEventListener('click', () => {
                        // Usamos la ruta corregida también aquí
                        fetch(imagePath)
                            .then(res => res.blob())
                            .then(blob => {
                                signatureToUpload = new File([blob], sig.path, { type: blob.type });
                                statusText.textContent = `Estado: Seleccionada la firma guardada '${sig.name}'.`;
                                console.log("Firma guardada seleccionada:", signatureToUpload);
                                document.querySelectorAll('.signature-item').forEach(el => el.classList.remove('selected'));
                                sigElement.classList.add('selected');
                            });
                    });
                    savedSignaturesList.appendChild(sigElement);
                });
            }
        })
        .catch(error => {
            console.error(error);
            savedSignaturesList.innerHTML = '<p>Error al cargar firmas.</p>';
        });
}

    // --- LÓGICA DE LOS BOTONES DE ACCIÓN ---

    clearButton.addEventListener('click', () => ctx.clearRect(0, 0, canvas.width, canvas.height));

    downloadButton.addEventListener('click', () => {
        const link = document.createElement('a');
        link.download = `firma-descargada-${Date.now()}.png`;
        link.href = canvas.toDataURL();
        link.click();
    });

    prepareCanvasButton.addEventListener('click', () => {
        canvas.toBlob(blob => {
            signatureToUpload = new File([blob], `firma-dibujada-${Date.now()}.png`, { type: 'image/png' });
            statusText.textContent = 'Estado: Lista para subir la firma dibujada actualmente.';
            document.querySelectorAll('.signature-item').forEach(el => el.classList.remove('selected'));
            console.log("Firma del canvas preparada:", signatureToUpload);
        });
    });

    saveNewSignatureButton.addEventListener('click', () => {
        const name = newSignatureNameInput.value.trim();
        if (!name) {
            alert('Por favor, dale un nombre a tu firma antes de guardarla.');
            return;
        }
        canvas.toBlob(blob => {
            const formData = new FormData();
            formData.append('signature_name', name);
            formData.append('signature_file', blob);
            fetch('/api/signatures', { method: 'POST', body: formData })
                .then(res => res.ok ? res.json() : Promise.reject('Error al guardar'))
                .then(data => {
                    alert('¡Firma guardada con éxito en tu perfil!');
                    newSignatureNameInput.value = '';
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    loadSavedSignatures();
                })
                .catch(error => alert('No se pudo guardar la firma.'));
        });
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            signatureToUpload = fileInput.files[0];
            statusText.textContent = `Estado: Listo para subir el archivo '${signatureToUpload.name}'.`;
            document.querySelectorAll('.signature-item').forEach(el => el.classList.remove('selected'));
            console.log("Archivo de firma preparado:", signatureToUpload);
        }
    });

    finalUploadButton.addEventListener('click', () => {
        if (documentInput.files.length === 0) {
            alert('Paso 1: Por favor, selecciona un documento para firmar.');
            return;
        }
        if (!signatureToUpload) {
            alert('Paso 2: Por favor, prepara una firma (dibujada, subida o seleccionada de tu galería).');
            return;
        }

        const documentFile = documentInput.files[0];
        const formData = new FormData();
        formData.append('document_file', documentFile);
        formData.append('signature_file', signatureToUpload);
        
        statusText.textContent = 'Subiendo documento y firma...';
        
        fetch('/upload_document', { method: 'POST', body: formData })
            .then(response => {
                if (!response.ok) throw new Error(`Error del servidor: ${response.statusText}`);
                return response.json();
            })
            .then(data => {
                alert(`¡Éxito! Archivo subido: ${data.file_path}`);
                statusText.textContent = '¡Subida completada! Listo para un nuevo documento.';
                signatureToUpload = null;
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                fileInput.value = '';
                documentInput.value = '';
                document.querySelectorAll('.signature-item').forEach(el => el.classList.remove('selected'));
            })
            .catch(error => {
                console.error('Error al subir:', error);
                alert(`Ocurrió un error al subir los archivos. ${error.message}`);
                statusText.textContent = `Estado: Error al subir. Intenta de nuevo.`;
            });
    });

    // Cargar las firmas guardadas al iniciar la página
    loadSavedSignatures();
});