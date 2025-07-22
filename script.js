const canvas = document.getElementById("experimentCanvas");
const ctx = canvas.getContext("2d");

const amplitudes = [300, 400]; // ejemplo en píxeles
const widths = [30, 60];       // diámetro del target
const trialsPerCombination = 9;


let trackingInterval = null;
let currentMousePosition = { x: 0, y: 0 };

let trialData = []; // array de todos los trials

let currentTrialS = {
  cursorPositions: [],
  movementStartTime: null,
  reachingTime: null,
  clickDownTime: null,
  clickUpTime: null,
  success: false,
  A: 0,
  W: 0,
  ID: 0,
  trialIndex: 0
};

let velocityChart = null;

let movementStarted = false;
let trackingStartTime = null;

let blocks = [];      // Cada bloque es una combinación A-W con T trials
let currentBlock = 0;
let currentTrial = 0;

let randomStart = 0;
let isExperimentStarted = false;
let feedbackMode = "none";
let targets = [];
let results = [];
let mousePositions = [];
let movementStartTime = null;
let data = [];

const startButton = {
  x: canvas.width / 2,
  y: canvas.height / 2,
  radius: 50,
};


document.getElementById("feedbackMode").addEventListener("change", updateFeedbackMode);
drawStartButton();

// Maneja clics
canvas.addEventListener("click", (e) => {
  const rect = canvas.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top;



  if (!isExperimentStarted) {
    if (isInsideCircle(clickX, clickY, startButton)) {
        startExperiment();
    }
    return;
  }

  handleClickOnTarget(clickX, clickY);
});


function generateBlocks() {
  blocks = [];


  
  for (let A of amplitudes) {
    for (let W of widths) {
     // for (let t = 0; t < trialsPerCombination; t++) {
        blocks.push({ A, W });
      //}
    }
  }

  // Aleatorizar el orden de bloques
  blocks = shuffleArray(blocks);
}


function shuffleArray(array) {
  return array
    .map(value => ({ value, sort: Math.random() }))
    .sort((a, b) => a.sort - b.sort)
    .map(({ value }) => value);
}

function generateRingTargets(A, W) {
  const N = 9;
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const angleStep = (2 * Math.PI) / N;


  const k = Math.floor(N / 2);
  const angleToOpposite = (2 * Math.PI * k) / N;
  const R = A / (2 * Math.sin(angleToOpposite / 2)); // fórmula clave

  targets = [];

  for (let i = 0; i < N; i++) {
    const angle = i * angleStep;
    const x = centerX + R * Math.cos(angle);
    const y = centerY + R * Math.sin(angle);

    targets.push({
      x,
      y,
      radius: W / 2,
    });
  }

  // Empezar alternancia en 0 y 5 (opuestos)
}

function nextTrial() {
  currentTrial++;
  if (currentTrial >= trialsPerCombination) {
    currentBlock++;
    currentTrial = 0;
    randomStart = Math.floor(Math.random() * 10); // reiniciar aleatorio entre 0 y 8
  }

  if (currentBlock >= blocks.length) {
    endExperiment();
    return;
  }

  const { A, W } = blocks[currentBlock];
  //stopCursorTracking();




  generateRingTargets(A, W);
  draw();


  const now = performance.now();

  currentTrialS.movementStartTime = now;
  trackingStartTime = now;
  movementStarted = true;

  //startCursorTracking();
}

function handleClickOnTarget(x, y) {
  //const activeTarget = targets[currentPair[currentTargetIndex]];
  const activeTarget = targets[(currentTrial + randomStart) * 5 % 9]; // Alterna entre los targets del par
  const dx = x - activeTarget.x;
  const dy = y - activeTarget.y;
  const distance = Math.sqrt(dx * dx + dy * dy);

  const success = distance <= activeTarget.radius;
  results.push({
    success,
    target: (currentTrial + randomStart) * 5 % 9,
    block: currentBlock,
    trial: currentTrial,
    A: blocks[currentBlock].A,
    W: blocks[currentBlock].W,
    time: performance.now(),
  });

  //logEvent(success ? "hit" : "miss");

  // Alternar al siguiente target del par (0 -> 1, 1 -> 0)
  

  //nextTrial();
}



canvas.addEventListener("mousemove", (e) => {
    if (!isExperimentStarted) return;

    const now = performance.now();
    if (trackingStartTime && now - trackingStartTime > 4000) return;
    const pos = { x: e.offsetX, y: e.offsetY, time: now };
    mousePositions.push(pos);

    currentTrialS.cursorPositions.push(pos);


    if (!movementStartTime) {
        currentTrialS.movementStartTime = now;
        movementStartTime = pos.time;
        movementStarted = true;
    }

    checkReaching(pos);
});

/*
canvas.addEventListener("mousemove", (e) => {
  const rect = canvas.getBoundingClientRect();
  currentMousePosition = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  };
});*/

function startCursorTracking() {
  const now = performance.now();

  currentTrialS.movementStartTime = now;
  trackingStartTime = now;
  movementStarted = true;

  trackingInterval = setInterval(() => {
    const time = performance.now();

    // Limita el tiempo de muestreo a 4 segundos
    if (time - trackingStartTime > 4000) {
      stopCursorTracking();
      return;
    }

    const pos = {
      x: currentMousePosition.x,
      y: currentMousePosition.y,
      time
    };

    currentTrialS.cursorPositions.push(pos);
    checkReaching(pos);
  }, 1); // cada 10 ms
}


function checkReaching(pos) {
    const target = targets[(currentTrial + randomStart)* 5 % 9]; // Alterna entre los targets del par
    const buffer = feedbackMode === "buffer" ? 10 : 0;
    const dx = pos.x - target.x;
    const dy = pos.y - target.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
  
    
    if (distance < target.radius + buffer) {
        target.hit = true;
        if(!currentTrialS.reachingTime) currentTrialS.reachingTime = pos.time;
    }
    else {
        target.hit = false;
    }
    draw();
}


function stopCursorTracking() {
  if (trackingInterval) {
    clearInterval(trackingInterval);
    trackingInterval = null;
  }
}



function drawStartButton() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.beginPath();
  ctx.arc(startButton.x, startButton.y, startButton.radius, 0, Math.PI * 2);
  ctx.fillStyle = "#007BFF";  // color azul
  ctx.fill();
  ctx.fillStyle = "white";
  ctx.font = "20px Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("Start", startButton.x, startButton.y);
}

function isInsideCircle(x, y, circle) {
  const dx = x - circle.x;
  const dy = y - circle.y;
  return Math.sqrt(dx * dx + dy * dy) <= circle.radius;
}



function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  targets.forEach((t, index) => {
    ctx.beginPath();
    ctx.arc(t.x, t.y, t.radius, 0, Math.PI * 2);
    const isActive = (((currentTrial + randomStart)*5 % 9) === index);
    const activeColor = (t.hit && feedbackMode != "none")? "#28a745" : "#007BFF"; // verde si hit, azul si no
    //const isActive = index === currentPair[currentTargetIndex];
    ctx.fillStyle = isActive ? activeColor: "gray";
    ctx.fill();
  });
}

function updateFeedbackMode() {
  const select = document.getElementById("feedbackMode");
  if (select) {
    feedbackMode = select.value;
  }
}


function endExperiment() {
  isExperimentStarted = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "24px Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.fillText("¡Experimento finalizado!", canvas.width / 2, canvas.height / 2);
  console.log("Resultados:", results);
}

function startExperiment() {
    randomStart = Math.floor(Math.random() * 10); // 0 a 9 aleatorio
    isExperimentStarted = true;
    results = [];
    data = [];
    mousePositions = [];
    currentBlock = 0;
    currentTrial = 0;
    generateBlocks();
    const { A, W } = blocks[0];
    generateRingTargets(A, W);
    draw();
    //startCursorTracking();  
}

canvas.addEventListener("mousedown", (e) => {
  if (!isExperimentStarted) return;
  currentTrialS.clickDownTime = performance.now();
  trackingStartTime = performance.now();
});
canvas.addEventListener("mouseup", (e) => {
  if (!isExperimentStarted) return;

  currentTrialS.clickUpTime = performance.now();

  //const dx = e.offsetX - targets[currentPair[currentTargetIndex]].x;
  //const dy = e.offsetY - targets[currentPair[currentTargetIndex]].y;
  const dx = e.offsetX - targets[(currentTrial + randomStart) * 5 % 9].x;
  const dy = e.offsetY - targets[(currentTrial + randomStart) * 5 % 9].y;
  const distance = Math.sqrt(dx * dx + dy * dy);
  currentTrialS.success = distance <= targets[(currentTrial + randomStart) * 5 % 9].radius;

  const block = blocks[currentBlock];
  currentTrialS.A = block.A;
  currentTrialS.W = block.W;
  currentTrialS.ID = Math.log2((2 * block.A) / block.W);
  //currentTrialS.trialIndex = currentTrial;

  currentTrialS.clickUpTime = currentTrialS.clickUpTime - currentTrialS.movementStartTime;
  currentTrialS.clickDownTime = currentTrialS.clickDownTime - currentTrialS.movementStartTime;
  if (currentTrialS.reachingTime) {
    currentTrialS.reachingTime = currentTrialS.reachingTime - currentTrialS.movementStartTime;
  }
  currentTrialS.confirmationTime = currentTrialS.clickUpTime;

  
  showTrialData(currentTrialS);

  // Reiniciar estado para siguiente trial
  currentTrialS = {
    cursorPositions: [],
    movementStartTime: null,
    reachingTime: null,
    clickDownTime: null,
    clickUpTime: null,
    success: false,
    A: 0,
    W: 0,
    ID: 0,
    trialIndex: 0
  };
  movementStarted = false;

  // Alternar target y avanzar
  

  nextTrial();
  
  



});


function showTrialData(trial) {
  const infoEl = document.getElementById("trialInfo");
  
  // Mostrar tiempos en números
  const lines = [
    `A: ${currentTrialS.A}`,
    `W: ${currentTrialS.W}`,
    `ID: ${currentTrialS.ID.toFixed(2)}`,
    `Reaching Time: ${currentTrialS.reachingTime?.toFixed(2)} ms`,
    `Confirmation Time: ${currentTrialS.confirmationTime?.toFixed(2)} ms`,
    `Click Duration: ${currentTrialS.clickDuration?.toFixed(2)} ms`,
    `Success: ${currentTrialS.success ? "✔️" : "❌"}`
  ];
  infoEl.textContent = lines.join("\n");

  // Calcular velocidad
  const speeds = [];
  const times = [];

  const positions = trial.cursorPositions;
  for (let i = 1; i < positions.length; i++) {
    const dx = positions[i].x - positions[i - 1].x;
    const dy = positions[i].y - positions[i - 1].y;
    const dt = positions[i].time - positions[i - 1].time;

    const speed = Math.sqrt(dx * dx + dy * dy) / dt; // px/ms
    speeds.push(speed * 1000); // px/s
    times.push(positions[i].time - positions[0].time);
  }

  drawSpeedChart(times, speeds, trial.reachingTime, trial.clickDownTime, trial.clickUpTime);
}



function createVerticalLineAnnotation(label, color, value) {
  return {
    type: 'line',
    scaleID: 'x',
    value: value.toFixed(0),
    borderColor: color,
    borderWidth: 2,
    label: {
      content: label,
      enabled: true,
      position: 'top'
    }
  };
}

function drawSpeedChart(times, speeds, reachingTime, clickDownTime, clickUpTime) {

  const ctx = document.getElementById("velocityChart").getContext("2d");

  if (velocityChart) {
    velocityChart.destroy();
  }

  const annotations = {};

  if (reachingTime) {
    annotations.reach = createVerticalLineAnnotation(
      "Reach",
      "orange",
      reachingTime 
    );
  }
  
  if (clickDownTime) {
    annotations.clickDown = createVerticalLineAnnotation(
      "MouseDown",
      "blue",
      clickDownTime 
    );
}

if (clickUpTime) {
  annotations.clickUp = createVerticalLineAnnotation(
    "MouseUp",
    "red",
    clickUpTime 
  );
}


  velocityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: times.map(t => t.toFixed(0)),
      datasets: [{
        label: "Velocidad (px/s)",
        data: times.map((t, i) => ({ x: t, y: speeds[i] })), // <-- usa objetos {x, y}
        fill: false,
        borderColor: "blue",
        pointRadius: 1,
        tension: 0.1
      }]
    },
    options: {
      responsive: false,
      plugins: {
        legend: { display: true },
        annotation: {
          annotations
        }
      },
      scales: {
        x: {
          type: 'linear', // <-- importante!
          title: { display: true, text: "Tiempo (ms)" }
        },
        y: {
          title: { display: true, text: "Velocidad (px/s)" }
        }
      }
    },
    plugins: [Chart.registry.getPlugin('annotation')]
  });
}

