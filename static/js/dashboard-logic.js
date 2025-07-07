// static/js/dashboard-logic.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Selectores de Elementos ---
    const signatureItems = document.querySelectorAll('.signature-item');
    const documentToSignInput = document.getElementById('document-to-sign-input');
    const loadDocumentBtn = document.getElementById('load-document-btn');
    const documentPreviewContainer = document.getElementById('document-preview-container');
    const signatureToApply = document.getElementById('signature-to-apply');
    const saveSignedDocumentBtn = document.getElementById('save-signed-document-btn');
    const dashboardStatusText = document.getElementById('dashboard-status-text');
    const signedDocumentsList = document.getElementById('signed-documents-list');

    // --- NUEVO: Selectores para el Modal de Vista Previa ---
    const previewModal = document.getElementById('preview-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalTitle = document.getElementById('modal-title');
    const previewArea = document.getElementById('preview-area');
    
    let selectedSignatureUrl = null;
    let currentDocumentFile = null;
    let isDraggingSignature = false;
    let signatureOffsetX, signatureOffsetY;

    // --- Funciones de Utilidad ---
    function showStatus(message, type = 'info') {
        dashboardStatusText.innerHTML = message;
        dashboardStatusText.className = 'status-message';
        dashboardStatusText.classList.add(type);
        dashboardStatusText.style.display = 'block';
    }

    // ... (El resto de las funciones de drag-and-drop y guardado permanecen igual) ...
        // --- 1. Selección de Firma ---
    signatureItems.forEach(item => {
        item.addEventListener('click', () => {
            signatureItems.forEach(sig => sig.classList.remove('selected'));
            item.classList.add('selected');
            selectedSignatureUrl = item.dataset.signatureUrl;
            signatureToApply.src = selectedSignatureUrl;
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
        documentPreviewContainer.innerHTML = '';
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
        formData.append('position_x', signatureToApply.style.left);
        formData.append('position_y', signatureToApply.style.top);
        formData.append('signature_width', `${signatureToApply.offsetWidth}px`);
        formData.append('preview_width', documentPreviewContainer.offsetWidth);
        formData.append('preview_height', documentPreviewContainer.offsetHeight);

        try {
            const response = await fetch('/sign_existing_document', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            if (response.ok && data.file_path) {
                showStatus(`¡Documento firmado con éxito!`, 'success');
                loadSignedDocuments(); 
                // Limpiar la interfaz
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

    // --- 5. Lógica para cargar y gestionar documentos firmados ---
    async function loadSignedDocuments() {
        try {
            const response = await fetch('/get_signed_documents');
            if (!response.ok) throw new Error('No se pudo cargar la lista de documentos.');

            const documents = await response.json();
            signedDocumentsList.innerHTML = ''; 

            if (documents.length === 0) {
                signedDocumentsList.innerHTML = '<p>No tienes documentos firmados todavía.</p>';
                return;
            }

            documents.forEach(doc => {
                const docElement = document.createElement('div');
                docElement.className = 'signed-document-item';
                docElement.id = `doc-${doc.id}`;
                const date = new Date(doc.created_at).toLocaleString('es-ES');

                docElement.innerHTML = `
                    <div class="document-info">
                        ${doc.original_filename}
                        <small>Firmado el: ${date}</small>
                    </div>
                    <div class="document-actions">
                        <button class="btn-action btn-preview" data-url="${doc.url}" data-filename="${doc.original_filename}">Ver</button>
                        <button class="btn-action btn-delete" data-id="${doc.id}" data-filename="${doc.signed_filename}">Eliminar</button>
                    </div>
                `;
                signedDocumentsList.appendChild(docElement);
            });
        } catch (error) {
            signedDocumentsList.innerHTML = `<p class="status-message error">Error al cargar documentos: ${error.message}</p>`;
        }
    }
    
    // --- NUEVO: Manejadores de eventos para el modal ---
    function handlePreviewDocument(event) {
        const target = event.target;
        if (!target.classList.contains('btn-preview')) return;

        const docUrl = target.dataset.url;
        const docFilename = target.dataset.filename;
        const fileExtension = docFilename.split('.').pop().toLowerCase();

        previewArea.innerHTML = ''; // Limpiar vista previa anterior
        modalTitle.textContent = `Vista Previa: ${docFilename}`;

        if (fileExtension === 'pdf') {
            const iframe = document.createElement('iframe');
            iframe.src = docUrl;
            previewArea.appendChild(iframe);
        } else if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(fileExtension)) {
            const img = document.createElement('img');
            img.src = docUrl;
            img.alt = `Vista previa de ${docFilename}`;
            previewArea.appendChild(img);
        } else {
            previewArea.innerHTML = `<p>La vista previa para este tipo de archivo no está disponible. <a href="${docUrl}" target="_blank">Descargar archivo</a>.</p>`;
        }

        previewModal.style.display = 'block';
    }

    function handleDeleteDocument(event) {
        const target = event.target;
        if (!target.classList.contains('btn-delete')) return;
        
        const docId = target.dataset.id;
        const filename = target.dataset.filename;

        if (!confirm(`¿Estás seguro de que quieres eliminar el documento? Esta acción no se puede deshacer.`)) {
            return;
        }

        fetch('/delete_document', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: docId, filename: filename }),
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (ok) {
                document.getElementById(`doc-${docId}`).remove();
                alert(data.message);
            } else {
                throw new Error(data.error || 'Error desconocido');
            }
        })
        .catch(error => alert(`No se pudo eliminar el documento: ${error.message}`));
    }

    // --- NUEVO: Event listeners para el modal y delegación de eventos en la lista ---
    signedDocumentsList.addEventListener('click', (event) => {
        handlePreviewDocument(event);
        handleDeleteDocument(event);
    });

    modalCloseBtn.addEventListener('click', () => {
        previewModal.style.display = 'none';
        previewArea.innerHTML = ''; // Limpiar para ahorrar memoria
    });
    
    window.addEventListener('click', (event) => {
        if (event.target === previewModal) {
            previewModal.style.display = 'none';
            previewArea.innerHTML = '';
        }
    });

    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && previewModal.style.display === 'block') {
            previewModal.style.display = 'none';
            previewArea.innerHTML = '';
        }
    });

    // Cargar los documentos firmados al iniciar la página
    loadSignedDocuments();
});