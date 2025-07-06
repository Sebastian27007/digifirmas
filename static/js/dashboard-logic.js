// static/js/dashboard-logic.js

document.addEventListener('DOMContentLoaded', () => {
    const signatureItems = document.querySelectorAll('.signature-item');
    const documentToSignInput = document.getElementById('document-to-sign-input');
    const loadDocumentBtn = document.getElementById('load-document-btn');
    const documentPreviewContainer = document.getElementById('document-preview-container');
    const signatureToApply = document.getElementById('signature-to-apply');
    const saveSignedDocumentBtn = document.getElementById('save-signed-document-btn');
    const dashboardStatusText = document.getElementById('dashboard-status-text');

    let selectedSignatureUrl = null;
    let currentDocumentFile = null;
    let isDraggingSignature = false;
    let signatureOffsetX, signatureOffsetY;

    // --- Funciones de Utilidad ---
    function showStatus(message, type = 'info') {
        // --- CORRECCIÓN: Usar innerHTML para renderizar el enlace de descarga ---
        dashboardStatusText.innerHTML = message;
        dashboardStatusText.className = 'status-message'; // Reset classes
        dashboardStatusText.classList.add(type);
        dashboardStatusText.style.display = 'block';
    }

    function hideStatus() {
        dashboardStatusText.style.display = 'none';
    }

    // --- 1. Selección de Firma ---
    signatureItems.forEach(item => {
        item.addEventListener('click', () => {
            signatureItems.forEach(sig => sig.classList.remove('selected'));
            item.classList.add('selected');

            selectedSignatureUrl = item.dataset.signatureUrl;
            signatureToApply.src = selectedSignatureUrl;
            
            // Mover la firma al contenedor de preview para que se pueda arrastrar sobre él
            documentPreviewContainer.appendChild(signatureToApply);
            signatureToApply.style.display = 'block';
            signatureToApply.style.left = '50px';
            signatureToApply.style.top = '50px';
            
            showStatus('Firma seleccionada. Ahora carga un documento y arrástrala.', 'success');
        });
    });

    // --- 2. Carga y Previsualización del Documento ---
    loadDocumentBtn.addEventListener('click', () => {
        if (documentToSignInput.files.length === 0) {
            showStatus('Por favor, selecciona un documento primero.', 'error');
            return;
        }

        currentDocumentFile = documentToSignInput.files[0];

        if (!currentDocumentFile) {
            showStatus('No se pudo acceder al archivo del documento. Intenta de nuevo.', 'error');
            return;
        }

        const fileURL = URL.createObjectURL(currentDocumentFile);
        documentPreviewContainer.innerHTML = ''; // Limpiar contenido anterior
        
        let previewElement;

        if (currentDocumentFile.type.startsWith('image/')) {
            previewElement = document.createElement('img');
            previewElement.src = fileURL;
            showStatus('Documento imagen cargado. Arrastra la firma a la posición deseada.', 'info');
        } else if (currentDocumentFile.type === 'application/pdf') {
            previewElement = document.createElement('iframe');
            previewElement.src = fileURL;
            showStatus('Documento PDF cargado. Arrastra la firma.', 'info');
        } else {
            showStatus('Tipo de archivo no soportado para previsualización. Sube una imagen o PDF.', 'error');
            documentPreviewContainer.innerHTML = '<p>Tipo de archivo no soportado para previsualización.</p>';
            currentDocumentFile = null;
            return;
        }
        
        previewElement.classList.add('document-preview-content');
        documentPreviewContainer.appendChild(previewElement);
        saveSignedDocumentBtn.style.display = 'inline-block';
    });

    // --- 3. Lógica de Arrastre de la Firma ---
    signatureToApply.addEventListener('mousedown', (e) => {
        if (!selectedSignatureUrl || !currentDocumentFile) {
            showStatus('Selecciona una firma y carga un documento primero.', 'error');
            return;
        }
        isDraggingSignature = true;
        signatureToApply.style.cursor = 'grabbing';
        
        const rect = signatureToApply.getBoundingClientRect();
        signatureOffsetX = e.clientX - rect.left;
        signatureOffsetY = e.clientY - rect.top;

        e.preventDefault(); 
    });

    // Usar el contenedor del preview para el mousemove asegura que las coordenadas sean relativas a él
    documentPreviewContainer.addEventListener('mousemove', (e) => {
        if (!isDraggingSignature) return;

        const containerRect = documentPreviewContainer.getBoundingClientRect();
        
        let newX = e.clientX - containerRect.left - signatureOffsetX;
        let newY = e.clientY - containerRect.top - signatureOffsetY;

        newX = Math.max(0, Math.min(newX, containerRect.width - signatureToApply.offsetWidth));
        newY = Math.max(0, Math.min(newY, containerRect.height - signatureToApply.offsetHeight));

        signatureToApply.style.left = `${newX}px`;
        signatureToApply.style.top = `${newY}px`;
    });
    
    // Escuchar el mouseup en todo el documento para soltar la firma en cualquier lugar
    document.addEventListener('mouseup', () => {
        if (isDraggingSignature) {
            isDraggingSignature = false;
            signatureToApply.style.cursor = 'grab';
        }
    });

    // --- 4. Guardar Documento Firmado ---
    saveSignedDocumentBtn.addEventListener('click', async () => {
        if (!currentDocumentFile || !selectedSignatureUrl) {
            showStatus('Carga un documento y selecciona una firma primero.', 'error');
            return;
        }

        showStatus('Firmando y guardando documento...', 'info');

        const formData = new FormData();
        formData.append('document_file', currentDocumentFile);
        formData.append('signature_url', selectedSignatureUrl);
        
        // --- CORRECCIÓN: Enviar las dimensiones del contenedor del preview al backend ---
        formData.append('position_x', signatureToApply.style.left);
        formData.append('position_y', signatureToApply.style.top);
        formData.append('signature_width', `${signatureToApply.offsetWidth}px`);
        formData.append('preview_width', documentPreviewContainer.offsetWidth); // Ancho real del visor
        formData.append('preview_height', documentPreviewContainer.offsetHeight); // Alto real del visor

        try {
            const response = await fetch('/sign_existing_document', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (response.ok && data.file_path) {
                showStatus(`¡Documento firmado con éxito! Puedes descargarlo aquí: <a href="${data.file_path}" target="_blank">Descargar</a>`, 'success');
                // Limpiar la interfaz después de un éxito
                currentDocumentFile = null;
                selectedSignatureUrl = null;
                documentToSignInput.value = '';
                documentPreviewContainer.innerHTML = '<p>Carga un documento para previsualizarlo aquí.</p>';
                signatureToApply.style.display = 'none';
                saveSignedDocumentBtn.style.display = 'none';
                signatureItems.forEach(sig => sig.classList.remove('selected'));

            } else {
                showStatus(`Error: ${data.error || 'Ocurrió un error desconocido.'}`, 'error');
            }
        } catch (error) {
            console.error('Error al firmar el documento:', error);
            showStatus(`Error al firmar el documento: ${error.message}`, 'error');
        }
    });
});
