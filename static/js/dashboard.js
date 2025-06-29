// Lógica JavaScript específica para el dashboard de documentos

document.addEventListener('DOMContentLoaded', () => {
    // Función para eliminar un documento
    // Esta función se llama desde el onclick del botón "Eliminar" en dashboard.html
    window.eliminarDocumento = function(uniqueId) {
        // Se usa confirm para una confirmación rápida. En una aplicación real, se usaría un modal personalizado.
        if (confirm('¿Estás seguro de que quieres eliminar este documento y sus archivos asociados? Esta acción es irreversible.')) {
            fetch(`/eliminar_documento/${uniqueId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                // No es necesario enviar un cuerpo si el ID está en la URL
            })
            .then(response => {
                if (!response.ok) {
                    // Si la respuesta no es OK, intenta leer el error del JSON para un mensaje más específico
                    return response.json().then(err => { throw new Error(err.error || 'Error desconocido al eliminar.'); });
                }
                return response.json();
            })
            .then(data => {
                // Muestra un mensaje de éxito
                alert(data.message);
                // Recargar la página para actualizar la lista de documentos después de la eliminación
                window.location.reload();
            })
            .catch(error => {
                console.error('Error al eliminar:', error);
                alert(`Ocurrió un error al eliminar el documento: ${error.message}`);
            });
        }
    };
});
