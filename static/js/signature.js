// signature.js - Versión Final con Gestión de Firmas Personales

document.addEventListener('DOMContentLoaded', () => {

    // --- VARIABLES Y ELEMENTOS ---
    const canvas = document.getElementById('signature-canvas');
    const clearButton = document.getElementById('clear-btn');
    const downloadButton = document.getElementById('download-btn');
    const prepareCanvasButton = document.getElementById('prepare-canvas-btn');
    
    // Elementos para guardar una nueva firma
    const newSignatureNameInput = document.getElementById('new-signature-name');
    const saveNewSignatureButton = document.getElementById('save-new-signature-btn');

    // Elementos para la galería de firmas guardadas
    const savedSignaturesList = document.getElementById('saved-signatures-list');

    // Elementos para el flujo de subida final
    const fileInput = document.getElementById('file-input');
    const documentInput = document.getElementById('document-input');
    const finalUploadButton = document.getElementById('final-upload-btn');
    const statusText = document.getElementById('status-text');

    // Comprobación de que todos los elementos existen
    if (!canvas || !clearButton || !downloadButton || !prepareCanvasButton || !newSignatureNameInput || !saveNewSignatureButton || !savedSignaturesList || !fileInput || !documentInput || !finalUploadButton || !statusText) {
        console.error("Error crítico: Uno o más elementos del HTML no se encontraron. Revisa los IDs.");
        return;
    }
    
    // Nuestra "memoria" para la firma que se va a subir
    let signatureToUpload = null;

    // --- LÓGICA DE DIBUJO (Sin cambios) ---
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
    function loadSavedSignatures() {
        savedSignaturesList.innerHTML = '<p>Cargando firmas...</p>';
        fetch('/api/signatures')
            .then(res => {
                if (!res.ok) throw new Error('No se pudieron cargar las firmas');
                return res.json();
            })
            .then(signatures => {
                savedSignaturesList.innerHTML = '';
                if (signatures.length === 0) {
                    savedSignaturesList.innerHTML = '<p>Aún no tienes firmas guardadas.</p>';
                    return;
                }
                signatures.forEach(sig => {
                    const sigElement = document.createElement('div');
                    sigElement.className = 'signature-item';
                    sigElement.innerHTML = `<img src="${sig.path}" alt="${sig.name}" title="${sig.name}"><span>${sig.name}</span>`;
                    
                    sigElement.addEventListener('click', () => {
                        fetch(sig.path)
                            .then(res => res.blob())
                            .then(blob => {
                                signatureToUpload = new File([blob], sig.path.split('/').pop(), { type: blob.type });
                                statusText.textContent = `Estado: Seleccionada la firma guardada '${sig.name}'.`;
                                document.querySelectorAll('.signature-item').forEach(el => el.classList.remove('selected'));
                                sigElement.classList.add('selected');
                            });
                    });
                    savedSignaturesList.appendChild(sigElement);
                });
            })
            .catch(error => {
                console.error(error);
                savedSignaturesList.innerHTML = '<p>Error al cargar firmas.</p>';
            });
    }

    // Botón para guardar una nueva firma en el perfil
    saveNewSignatureButton.addEventListener('click', () => {
        const name = newSignatureNameInput.value.trim();
        if (!name) {
            alert('Por favor, dale un nombre a tu firma antes de guardarla.');
            return;
        }
        canvas.toBlob(blob => {
            const formData = new FormData();
            formData.append('signature_name', name);
            formData.append('signature_file', blob, `${name}.png`);

            fetch('/api/signatures', { method: 'POST', body: formData })
                .then(res => res.ok ? res.json() : Promise.reject('Error al guardar la firma.'))
                .then(data => {
                    alert('¡Firma guardada con éxito en tu perfil!');
                    newSignatureNameInput.value = '';
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    loadSavedSignatures(); // Recargar la galería para mostrar la nueva firma
                })
                .catch(error => alert(error));
        });
    });

    // --- LÓGICA DE BOTONES DE ACCIÓN DEL CANVAS ---
    clearButton.addEventListener('click', () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    });

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
        });
    });

    // --- LÓGICA DE SUBIDA FINAL ---
    finalUploadButton.addEventListener('click', () => {
        // ... (Tu lógica de subida final que ya tenías funciona aquí sin cambios)...
        // ... ya que todos los flujos actualizan la variable `signatureToUpload`.
    });

    // Cargar las firmas guardadas al iniciar la página
    loadSavedSignatures();
});