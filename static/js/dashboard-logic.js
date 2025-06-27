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
        dashboardStatusText.textContent = message;
        dashboardStatusText.classList.remove('success', 'error', 'info');
        dashboardStatusText.classList.add(type);
        dashboardStatusText.style.display = 'block';
    }

    function hideStatus() {
        dashboardStatusText.style.display = 'none';
    }

    // --- 1. Selección de Firma ---
    signatureItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remover la clase 'selected' de todos los ítems
            signatureItems.forEach(sig => sig.classList.remove('selected'));
            // Añadir la clase 'selected' al ítem clickeado
            item.classList.add('selected');

            selectedSignatureUrl = item.dataset.signatureUrl;
            signatureToApply.src = selectedSignatureUrl;
            signatureToApply.style.display = 'block';
            signatureToApply.style.left = '50px'; // Posición inicial
            signatureToApply.style.top = '50px'; // Posición inicial
            
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
        const fileURL = URL.createObjectURL(currentDocumentFile);

        // Limpiar previsualización anterior y la firma flotante
        documentPreviewContainer.innerHTML = '<p>Carga un documento para previsualizarlo aquí.</p>';
        signatureToApply.style.display = 'none'; // Ocultar hasta que se posicione sobre el nuevo doc
        documentPreviewContainer.appendChild(signatureToApply); // Asegurarse de que la firma esté dentro del contenedor

        if (currentDocumentFile.type.startsWith('image/')) {
            const img = document.createElement('img');
            img.src = fileURL;
            img.classList.add('document-img'); // Para aplicar estilos
            documentPreviewContainer.innerHTML = ''; // Limpiar el párrafo
            documentPreviewContainer.appendChild(img);
            documentPreviewContainer.appendChild(signatureToApply); // Volver a añadir la firma por encima
            saveSignedDocumentBtn.style.display = 'inline-block'; // Mostrar botón de guardar
            showStatus('Documento imagen cargado. Arrastra la firma a la posición deseada.', 'info');

        } else if (currentDocumentFile.type === 'application/pdf') {
            // Para PDFs, usar un iframe es una solución sencilla pero limita la interactividad.
            // Para incrustar directamente en el cliente, necesitarías PDF.js y un canvas.
            const iframe = document.createElement('iframe');
            iframe.src = fileURL;
            iframe.style.width = '100%';
            iframe.style.height = '100%';
            iframe.style.border = 'none';
            documentPreviewContainer.innerHTML = '';
            documentPreviewContainer.appendChild(iframe);
            documentPreviewContainer.appendChild(signatureToApply); // Añadir la firma por encima del iframe

            saveSignedDocumentBtn.style.display = 'inline-block';
            showStatus('Documento PDF cargado. Arrastra la firma. (La firma se aplicará en el servidor).', 'info');
            
            // Advertencia: Posicionar la firma visualmente sobre un iframe no es exacto para el PDF real.
            // Lo ideal sería renderizar el PDF a un canvas y luego superponer la firma en ese canvas.
            // O, si es un PDF complejo, el usuario solo indicaría las coordenadas, y el backend haría el resto.
            // Para este ejemplo, asumiremos que las coordenadas relativas del div son suficientes.

        } else {
            showStatus('Tipo de archivo no soportado para previsualización. Sube una imagen o PDF.', 'error');
            documentPreviewContainer.innerHTML = '<p>Tipo de archivo no soportado para previsualización.</p>';
            saveSignedDocumentBtn.style.display = 'none';
            currentDocumentFile = null;
        }
    });

    // --- 3. Lógica de Arrastre de la Firma ---
    signatureToApply.addEventListener('mousedown', (e) => {
        if (!selectedSignatureUrl || !currentDocumentFile) {
            showStatus('Selecciona una firma y carga un documento primero.', 'error');
            return;
        }
        isDraggingSignature = true;
        signatureToApply.style.cursor = 'grabbing';
        
        // Calcular el offset inicial del clic dentro de la imagen de la firma
        const rect = signatureToApply.getBoundingClientRect();
        signatureOffsetX = e.clientX - rect.left;
        signatureOffsetY = e.clientY - rect.top;

        // Prevenir el comportamiento de arrastre predeterminado del navegador
        e.preventDefault(); 
    });

    documentPreviewContainer.addEventListener('mousemove', (e) => {
        if (!isDraggingSignature) return;

        // Obtener las dimensiones del contenedor de previsualización
        const containerRect = documentPreviewContainer.getBoundingClientRect();
        
        // Calcular las nuevas posiciones de la firma relativas al contenedor
        let newX = e.clientX - containerRect.left - signatureOffsetX;
        let newY = e.clientY - containerRect.top - signatureOffsetY;

        // Limitar el arrastre para que la firma no salga del contenedor
        newX = Math.max(0, Math.min(newX, containerRect.width - signatureToApply.offsetWidth));
        newY = Math.max(0, Math.min(newY, containerRect.height - signatureToApply.offsetHeight));

        signatureToApply.style.left = `${newX}px`;
        signatureToApply.style.top = `${newY}px`;
    });

    document.addEventListener('mouseup', () => {
        if (isDraggingSignature) {
            isDraggingSignature = false;
            signatureToApply.style.cursor = 'grab';
            showStatus('Firma posicionada. Puedes arrastrarla de nuevo o guardar el documento.', 'info');
        }
    });

    // --- 4. Guardar Documento Firmado ---
    saveSignedDocumentBtn.addEventListener('click', async () => {
        if (!currentDocumentFile) {
            showStatus('Primero carga un documento.', 'error');
            return;
        }
        if (!selectedSignatureUrl) {
            showStatus('Primero selecciona una firma.', 'error');
            return;
        }
        if (signatureToApply.style.display === 'none') {
             showStatus('La firma no está visible. Arrastra la firma sobre el documento para posicionarla.', 'error');
             return;
        }

        showStatus('Firmando y guardando documento...', 'info');

        const formData = new FormData();
        formData.append('document_file', currentDocumentFile);
        formData.append('signature_url', selectedSignatureUrl); // La URL completa de la firma guardada
        
        // Enviar las posiciones actuales de la firma (relativas al contenedor del preview)
        // Y las dimensiones actuales de la firma tal como se muestra en el cliente
        formData.append('position_x', signatureToApply.style.left);
        formData.append('position_y', signatureToApply.style.top);
        formData.append('signature_width', `${signatureToApply.offsetWidth}px`);
        formData.append('signature_height', `${signatureToApply.offsetHeight}px`);


        try {
            const response = await fetch('/sign_existing_document', { // Nueva ruta en app.py
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (response.ok && data.message) {
                showStatus(`¡Documento firmado! ${data.message}. Puedes descargarlo aquí: <a href="${data.file_path}" target="_blank">Descargar</a>`, 'success');
                // Limpiar la interfaz después de un éxito
                currentDocumentFile = null;
                selectedSignatureUrl = null;
                documentToSignInput.value = '';
                documentPreviewContainer.innerHTML = '<p>Carga un documento para previsualizarlo aquí.</p>';
                signatureToApply.style.display = 'none';
                saveSignedDocumentBtn.style.display = 'none';
                // Deseleccionar la firma en la lista
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