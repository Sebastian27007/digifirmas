const canvas = document.getElementById('signature-canvas');
const ctx = canvas.getContext('2d');
let drawing = false;

canvas.addEventListener('mousedown', () => { drawing = true; });
canvas.addEventListener('mouseup', () => { drawing = false; ctx.beginPath(); });
canvas.addEventListener('mouseout', () => { drawing = false; ctx.beginPath(); });
canvas.addEventListener('mousemove', draw);

function draw(e) {
    if (!drawing) return;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';

    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
}

function clearCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function saveSignature() {
    const dataURL = canvas.toDataURL('image/png');
    const formData = new FormData();
    formData.append('imageData', dataURL);

    fetch('/save_signature', {
        method: 'POST',
        body: formData
    })
    .then(res => res.text())
    .then(msg => alert(msg))
    .catch(err => console.error('Error:', err));
}
document.getElementById('uploadForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);

    fetch('/upload_signature', {
        method: 'POST',
        body: formData
    })
    .then(res => res.text())
    .then(msg => alert(msg))
    .catch(err => console.error('Error al subir imagen:', err));
});