document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('signature-canvas');
    if (!canvas) return; // Si no hay canvas, no hagas nada.
    
    const ctx = canvas.getContext('2d');
    let drawing = false;

    // Ajusta el tamaño para evitar dibujos borrosos
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    
    // Estilo del lápiz
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';

    // --- LÓGICA DE DIBUJO ---
    function startPosition(e) {
        drawing = true;
        draw(e);
    }

    function endPosition() {
        drawing = false;
        ctx.beginPath();
    }

    function draw(e) {
        if (!drawing) return;
        e.preventDefault(); // Previene el scroll en móviles

        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX || e.touches[0].clientX) - rect.left;
        const y = (e.clientY || e.touches[0].clientY) - rect.top;

        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, y);
    }

    // Eventos para el dibujo con mouse y táctil
    canvas.addEventListener('mousedown', startPosition);
    canvas.addEventListener('mouseup', endPosition);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseleave', endPosition);
    canvas.addEventListener('touchstart', startPosition);
    canvas.addEventListener('touchend', endPosition);
    canvas.addEventListener('touchmove', draw);

    // --- LÓGICA DE LOS BOTONES ---
    const clearButton = document.getElementById('clear-btn');
    const saveButton = document.getElementById('save-btn');

    if (clearButton) {
        clearButton.addEventListener('click', () => {
            console.log("Botón Borrar presionado");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        });
    }

    if (saveButton) {
        saveButton.addEventListener('click', () => {
            console.log("Botón Guardar presionado para descargar imagen.");
            const signatureDataUrl = canvas.toDataURL('image/png');
            const downloadLink = document.createElement('a');
            downloadLink.href = signatureDataUrl;
            downloadLink.download = `firma-${Date.now()}.png`;
            downloadLink.click();
        });
    }
});