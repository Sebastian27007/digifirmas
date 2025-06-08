// Espera a que la página HTML esté completamente cargada.
document.addEventListener('DOMContentLoaded', () => {

    // 1. OBTENER EL CANVAS Y SU CONTEXTO
    // Seleccionamos el elemento <canvas> del HTML por su ID.
    const canvas = document.getElementById('signature-canvas');
    // Obtenemos el "contexto 2D", que es la herramienta que nos permite dibujar.
    const ctx = canvas.getContext('2d');

    // 2. CONFIGURACIÓN INICIAL
    // Una variable para saber si el usuario está dibujando o no.
    let drawing = false;

    // Ajustamos el tamaño del canvas para evitar que el dibujo se vea borroso.
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    // Definimos el estilo de la línea (grosor, color y terminación).
    ctx.lineWidth = 3;
    ctx.lineCap = 'round'; // Hace que los extremos de la línea sean redondeados.
    ctx.strokeStyle = '#000'; // Color del trazo.

    // 3. FUNCIONES PRINCIPALES DE DIBUJO

    // Función que se ejecuta cuando el usuario presiona el mouse o toca la pantalla.
    function startPosition(e) {
        drawing = true; // Empezamos a dibujar.
        draw(e); // Llamamos a draw() para que se pueda dibujar un solo punto.
    }

    // Función que se ejecuta cuando el usuario suelta el mouse o levanta el dedo.
    function endPosition() {
        drawing = false; // Dejamos de dibujar.
        ctx.beginPath(); // Reiniciamos el trazo para que la siguiente línea no se conecte con esta.
    }

    // Función que dibuja la línea mientras el mouse/dedo se mueve.
    function draw(e) {
        if (!drawing) return; // Si no estamos en modo "dibujo", no hace nada.

        // Prevenimos que la página haga scroll en móviles mientras se dibuja.
        e.preventDefault();

        // Calculamos la posición exacta del cursor dentro del canvas.
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX || e.touches[0].clientX) - rect.left;
        const y = (e.clientY || e.touches[0].clientY) - rect.top;

        ctx.lineTo(x, y); // Define el final de la línea.
        ctx.stroke();     // Dibuja la línea en el canvas.
        ctx.beginPath();  // Inicia un nuevo trazo.
        ctx.moveTo(x, y); // Mueve el "pincel" a la posición actual.
    }

    // 4. EVENT LISTENERS: Conectamos las funciones con las acciones del usuario.

    // Eventos para el mouse (escritorio)
    canvas.addEventListener('mousedown', startPosition);
    canvas.addEventListener('mouseup', endPosition);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseleave', endPosition); // Si el cursor sale del canvas, deja de dibujar.

    // Eventos para pantallas táctiles (móviles)
    canvas.addEventListener('touchstart', startPosition);
    canvas.addEventListener('touchend', endPosition);
    canvas.addEventListener('touchmove', draw);

});