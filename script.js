const canvas = document.getElementById("experimentCanvas");
const ctx = canvas.getContext("2d");

let feedbackMode = "none";
let targets = [];
let currentTargetIndex = 0;
let mousePositions = [];
let movementStartTime = null;
let data = [];

document.getElementById("feedbackMode").addEventListener("change", e => {
  feedbackMode = e.target.value;
});

canvas.addEventListener("mousemove", (e) => {
  const pos = { x: e.offsetX, y: e.offsetY, time: performance.now() };
  mousePositions.push(pos);

  // Detect first movement
  if (!movementStartTime) {
    movementStartTime = pos.time;
  }

  checkCollision(pos);
});

canvas.addEventListener("mousedown", (e) => {
  logEvent("mousedown");
});

canvas.addEventListener("mouseup", (e) => {
  logEvent("mouseup");
});

function logEvent(type) {
  data.push({
    type,
    time: performance.now(),
    target: currentTargetIndex
  });
}

function checkCollision(pos) {
  const target = targets[currentTargetIndex];
  const buffer = feedbackMode === "buffer" ? 10 : 0;
  const dx = pos.x - target.x;
  const dy = pos.y - target.y;
  const distance = Math.sqrt(dx * dx + dy * dy);

  if (distance < target.radius + buffer) {
    if (feedbackMode !== "none") {
      target.hit = true;
      draw();
      logEvent("collision");
      logEvent("feedback");
    }
  }
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (let t of targets) {
    ctx.beginPath();
    ctx.arc(t.x, t.y, t.radius, 0, Math.PI * 2);
    ctx.fillStyle = t.hit ? "green" : "gray";
    ctx.fill();
  }
}

function generateTargets() {
  targets = [
    { x: 100, y: 300, radius: 20, hit: false },
    { x: 700, y: 300, radius: 40, hit: false }
    // puedes generar más objetivos
  ];
  draw();
}

function downloadCSV() {
  let csv = "event,time,target\n";
  data.forEach(d => {
    csv += `${d.type},${d.time},${d.target}\n`;
  });
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = "resultados_fitts.csv";
  a.click();
}

generateTargets();
