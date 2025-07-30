
// Pariticipant ID
let participantId = crypto.randomUUID();

// UI elements
const canvas = document.getElementById("experimentCanvas");
const ctx = canvas.getContext("2d");

//Experiment variables
const indicationMethods = ["click", "barspace"];


const feedbacks = [
    {feedbackMode : "none",
      buffer: [0]
    }, 
    {feedbackMode : "green",
      buffer: [0, 10]
    }
];

const amplitudes = [238, 336, 672]; 
const widths = [21, 42, 84];       
const trialsPerCombination = 11;



let isExperimentDone = false;
let isExperimentStarted = false;
let firstTrial = true;
let trackingInterval = null;
let currentMousePosition = { x: 0, y: 0 };

let trialData = []; 
let currentTrialS = {
  feedbackMode: null,
  buffer: 0,
  indication: null,
  cursorPositions: [],
  cursorPositionsInterval: [], // array de posiciones del cursor
  movementStartTime: null,
  reachingTimes: [],
  outTimes: [],
  inTarget: false,
  clickDownTime: null,
  clickUpTime: null,
  success: false,
  A: 0,
  W: 0,
  ID: 0,
  trialIndex: 0
};

let velocityChart = null;
let velocityChart2 = null;

let movementStarted = false;
let trackingStartTime = null;


let indicationConditions = shuffleArray(indicationMethods); // aleatorizar el orden de las condiciones de indicación
let feedbackConditions = []; // array de condiciones de feedback
let blocks = [];      // Cada bloque es una combinación A-W con T trials
let currentBlock = 0;
let currentTrial = 0;
let currentCondition = 0; // índice de la condición actual
let currentIndication = 0;

let randomStart = 0;
//let feedbackMode = "none";
let targets = [];
let movementStartTime = null;
let data = [];

const startButton = {
  x: canvas.width / 2,
  y: canvas.height / 2,
  radius: 50,
};


drawStartButton();

// Maneja clics
canvas.addEventListener("click", (e) => {
  const rect = canvas.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top;



  if (!isExperimentStarted && !isExperimentDone) {
    if (isInsideCircle(clickX, clickY, startButton)) {
        startExperiment();
        
    }
    return;
  }
  if(firstTrial) {
    firstTrial = false;
     // No hacer nada en el primer click
  }
  //handleClickOnTarget(clickX, clickY);
});


function generateConditions(orderIndex) {
  feedbackConditions = [];
  for (let i = 0; i < indicationConditions.length; i++) {
    const indication = indicationConditions[i];
    for (let feedback of feedbacks) {
      for (let buf of feedback.buffer) {
        feedbackConditions.push({ feedbackMode: feedback.feedbackMode, buffer: buf, indication: indication });
      }
    }
  }
  // Latin Square rotation (modulo N)
  const N = feedbackConditions.length;
  feedbackConditions = [...Array(N)].map((_, i) => feedbackConditions[(i + orderIndex) % N]);

  return feedbackConditions;

}

function generateBlocks() {
  blocks = [];

  currentFeedback = feedbackConditions[currentCondition];
  currentBuffer = currentFeedback.buffer;
  currentFeedbackMode = currentFeedback.feedbackMode;
  //for (let feedback of feedbacks) {
  //    let feedbackMode = feedback.feedbackMode;
  //    for(let buf of feedback.buffer){
          for (let A of amplitudes) {
            for (let W of widths) {
              blocks.push({ A, W, feedbackMode: currentFeedbackMode, buffer: currentBuffer });
            }
          }
      //  }
    //}
  
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
    firstTrial = true; 
    randomStart = Math.floor(Math.random() * 10); // reiniciar aleatorio entre 0 y 8
  }
  stopCursorTracking();
  if (currentBlock >= blocks.length) {
    currentCondition++;
    if (currentCondition >= feedbackConditions.length) {
      endExperiment();
      return;
    }
    currentBlock = 0;
    currentTrial = 0;
    firstTrial = true; // Reiniciar el primer trial
    generateBlocks();
  }

  const { A, W, feedbackMode, buffer, indication } = blocks[currentBlock];




  generateRingTargets(A, W);
  draw();


  const now = performance.now();

  currentTrialS.movementStartTime = now;
  currentTrialS.feedbackMode = feedbackMode;
  currentTrialS.buffer = buffer;
  currentTrialS.indication = indication;
  trackingStartTime = now;
  movementStarted = true;
   startCursorTracking();
}

function handleClickOnTarget(x, y) {
  //const activeTarget = targets[currentPair[currentTargetIndex]];
  if(firstTrial) {
    firstTrial = false;
     // No hacer nada en el primer click
  }
  const activeTarget = getCurrentTarget(); // Alterna entre los targets del par
  const dx = x - activeTarget.x;
  const dy = y - activeTarget.y;
  const distance = Math.sqrt(dx * dx + dy * dy);

  const success = distance <= activeTarget.radius;

  //logEvent(success ? "hit" : "miss");

  // Alternar al siguiente target del par (0 -> 1, 1 -> 0)
  

  //nextTrial();
}



canvas.addEventListener("mousemove", (e) => {
    if (!isExperimentStarted) return;

    const now = performance.now();
    if (trackingStartTime && now - trackingStartTime > 4000) return;
    const pos = { x: e.offsetX, y: e.offsetY, time: now };
    currentMousePosition = {
      x: e.offsetX,
      y: e.offsetY
    };

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

    currentMousePosition = {
      x: currentMousePosition.x,
      y: currentMousePosition.y,
      time
    };

    //currentTrialS.cursorPositionsInterval.push(pos);
    //checkReaching(pos);
  }, 1); // cada 10 ms
}


function checkReaching(pos) {
    const target = getCurrentTarget(); // Alterna entre los targets del par
    const buffer = currentTrialS.buffer || 0; // buffer de colisión
    const dx = pos.x - target.x;
    const dy = pos.y - target.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
  
    
    if (distance < target.radius + buffer) {
        target.hit = true;

        if(!currentTrialS.inTarget){
          currentTrialS.inTarget = true;
          currentTrialS.reachingTimes.push(pos.time - currentTrialS.movementStartTime);
        } 
    }
    else {
        target.hit = false;
        if(currentTrialS.inTarget){
          currentTrialS.inTarget = false;
          currentTrialS.outTimes.push(pos.time - currentTrialS.movementStartTime);
        }
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

 // Draw instructions
  ctx.font = "18px Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  const instructions = [
    "Welcome to the Fitts' Law Game!",
    "Your task is to reach the targets as quickly and accurately as possible using the pointer.",
    "You will need to select using a click or barspace",
    "according to the conditon displayed in the top-left corner.",
    "The first target of each set will be YELLOW.",
    "Timing does NOT start until you reach the yellow target.",
    "After clicking Start, the set will begin.",
    "The target may or may not change color when reached,",
    "as shown by the feedback indicator in the top-left corner.",
    "Make sure the browser zoom is set to 100% for accurate results.",
  ];
  let y = startButton.y + startButton.radius + 30;
  for (let line of instructions) {
    ctx.fillText(line, canvas.width / 2, y);
    y += 28;
  }

   // --- Indicador de feedback en la esquina superior izquierda ---
    const indicatorX = 30;
    const indicatorY = 30;
    const circleRadius = 10;

    // Dibuja círculo
    ctx.beginPath();
    ctx.arc(indicatorX, indicatorY, circleRadius, 0, Math.PI * 2);
    ctx.fillStyle = "#007BFF";
    ctx.fill();

    
    ctx.beginPath();
    ctx.arc( indicatorX , 2 * indicatorY, circleRadius, 0, Math.PI * 2);
    ctx.fillStyle = "#28a745";
    ctx.fill();

    // Dibuja texto
    ctx.font = "16px Arial";
    ctx.fillStyle = "black";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText(`Feedback: None `, indicatorX + 20,  indicatorY);
    ctx.fillText(`Feedback: Green `, indicatorX + 20,  2 * indicatorY);
    ctx.fillText(`Indication: Click `, indicatorX + 20,  3* indicatorY);
    ctx.fillText(`Indication: Barspace `, indicatorX + 20,  4 * indicatorY);

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

    const activeColor = (t.hit && feedbackConditions[currentCondition].feedbackMode != "none")? "#28a745" : "#007BFF"; // verde si hit, azul si no

    let color = "gray";
    if( isActive) {
      color = activeColor;
      if(firstTrial) {
        color = "yellow"; // amarillo para el primer trial
      } 
    }
    ctx.fillStyle = color;
    ctx.fill();
  });

   // --- Indicador de feedback en la esquina superior izquierda ---
  const indicatorX = 30;
  const indicatorY = 30;
  const circleRadius = 10;
  const feedback = feedbackConditions[currentCondition].feedbackMode || "none";
  const indication = feedbackConditions[currentCondition].indication || "none";
  const circleColor = (feedback === "none") ? "#007BFF" : "#28a745"; // azul o verde

  // Dibuja círculo
  ctx.beginPath();
  ctx.arc(indicatorX, indicatorY, circleRadius, 0, Math.PI * 2);
  ctx.fillStyle = circleColor;
  ctx.fill();

  // Dibuja texto
  ctx.font = "16px Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(`Feedback: ${feedback}`, indicatorX + 20, indicatorY);
  ctx.fillText(`Selection: ${indication}`, indicatorX + 20, indicatorY + 20);

}

function updateFeedbackMode() {
  const select = document.getElementById("feedbackMode");
  if (select) {
    feedbackMode = select.value;
  }
}


async function endExperiment() {
  isExperimentStarted = false;
  isExperimentDone = true;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "24px Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.fillText("¡Experiment finished!", canvas.width / 2, canvas.height / 2);
  document.getElementById("velocityChart").style.display = "block";
  try {
    if (participantId) {
      await db.collection("participants").doc(participantId).update({
        completed: true,
        endedAt: new Date().toISOString()
      });
    }
  } catch (err) {
    console.error("Error al actualizar participante:", err);
  }
}

async function startExperiment() {
    randomStart = Math.floor(Math.random() * 10); // 0 a 9 aleatorio
    isExperimentStarted = true;
    data = [];
    currentBlock = 0;
    currentTrial = 0;
    await initializeParticipant();

    generateBlocks();
    const { A, W } = blocks[0];
    generateRingTargets(A, W);
    draw();
   //startCursorTracking();  
}

canvas.addEventListener("mousedown", (e) => {
  if(feedbackConditions[currentCondition].indication === "click") {
    indicationDown();
      if(firstTrial) {
    firstTrial = false;
     // No hacer nada en el primer click
  }
  }
});


function indicationDown() {
  if (!isExperimentStarted || isExperimentDone) return;
  currentTrialS.clickDownTime = performance.now();
  trackingStartTime = performance.now();
}

function indicationUp() {
  if (!isExperimentStarted || isExperimentDone) return; 
 /*   if(firstTrial) {
    firstTrial = false;
    currentTrial++; // Avanzar al siguiente trial
    draw(); // Redibujar para el siguiente trial
    return; // No hacer nada en el primer click
  }*/
  currentTrialS.clickUpTime = performance.now();
  //const dx = e.offsetX - getCurrentTarget().x;
  //const dy = e.offsetY - getCurrentTarget().y;
  const dx = currentMousePosition.x - getCurrentTarget().x;
  const dy = currentMousePosition.y - getCurrentTarget().y;
  const distance = Math.sqrt(dx * dx + dy * dy);
  currentTrialS.success = distance <= getCurrentTarget().radius;
  const block = blocks[currentBlock];
  currentTrialS.A = block.A;
  currentTrialS.W = block.W;
  currentTrialS.ID = Math.log2((2 * block.A) / block.W);
  currentTrialS.clickUpTime = currentTrialS.clickUpTime - currentTrialS.movementStartTime;
  currentTrialS.clickDownTime = currentTrialS.clickDownTime - currentTrialS.movementStartTime;
  currentTrialS.confirmationTime = currentTrialS.clickUpTime;
  trialData.push(currentTrialS);
  showTrialData(currentTrialS);
  saveTrialToFirestore(currentTrialS);


  currentTrialS = {
    feedbackMode: null,
    buffer: 0,
    indication: null,
    cursorPositions: [],
    cursorPositionsInterval: [],
    movementStartTime: null,
    reachingTimes: [],
    outTimes: [],
    inTarget: false,
    clickDownTime: null,
    clickUpTime: null,
    success: false,
    A: 0,
    W: 0,
    ID: 0,
    trialIndex: 0
  };
  movementStarted = false;

  nextTrial();
  

}

function getCurrentTarget() {
  return targets[(currentTrial + randomStart) * 5 % 9]; // Alterna entre los targets del par
}

canvas.addEventListener("mouseup", (e) => {


  if(feedbackConditions[currentCondition].indication === "click") {
    indicationUp();
  }

});

document.addEventListener("keydown", function(e) {
  if (e.code === "Space" || e.key === " " || e.key === "Spacebar") {
    if(feedbackConditions[currentCondition].indication === "barspace") {
      indicationDown();
    }
  }
});


document.addEventListener("keyup", function(e) {
  if (e.code === "Space" || e.key === " " || e.key === "Spacebar") {
    if(feedbackConditions[currentCondition].indication === "barspace") {
      indicationUp();
    }
  }
});

function showTrialData(trial) {
  const infoEl = document.getElementById("trialInfo");
  
  const lastReachingTime = trial.reachingTimes.length > 0 ? trial.reachingTimes[trial.reachingTimes.length - 1] : null;
  const lastOutTime = trial.outTimes.length > 0 ? trial.outTimes[trial.outTimes.length - 1] : null;

  // Mostrar tiempos en números
  const lines = [
    `Feedback: ${currentTrialS.feedbackMode}`,
    `A: ${currentTrialS.A}`,
    `W: ${currentTrialS.W}`,
    `ID: ${currentTrialS.ID.toFixed(2)}`,
    `Reaching Time: ${lastReachingTime?.toFixed(2)} ms`,
    `Out Time: ${lastOutTime?.toFixed(2)} ms`,
    `Confirmation Time: ${currentTrialS.confirmationTime?.toFixed(2)} ms`,
    `Click Duration: ${currentTrialS.clickDuration?.toFixed(2)} ms`,
    `Success: ${currentTrialS.success ? "✔️" : "❌"}`
  ];
  infoEl.textContent = lines.join("\n");

  
  //const positions = trial.cursorPositions;
  

  const { speeds, times } = getSpeedData(trial.cursorPositions);
  velocityChart = drawSpeedChart("velocityChart", times, speeds, trial.reachingTimes, trial.outTimes, trial.clickDownTime, trial.clickUpTime, velocityChart);

  const { speeds: speedsInterval, times: timesInterval } = getSpeedData(trial.cursorPositionsInterval);
  velocityChart2 = drawSpeedChart("velocityChart2", timesInterval, speedsInterval, trial.reachingTimes, trial.outTimes, trial.clickDownTime, trial.clickUpTime, velocityChart2);
}

function getSpeedData(positions) {
  const speeds = [];
  const times = [];
  for (let i = 1; i < positions.length; i++) {
    const dx = positions[i].x - positions[i - 1].x;
    const dy = positions[i].y - positions[i - 1].y;
    const dt = positions[i].time - positions[i - 1].time;

    const speed = Math.sqrt(dx * dx + dy * dy) / dt; // px/ms
    speeds.push(speed * 1000); // px/s
    times.push(positions[i].time - positions[0].time);
  }
  return { speeds, times };
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

function drawSpeedChart(chartName, times, speeds, reachingTimes, outTimes, clickDownTime, clickUpTime, oldChart) {

  const ctx = document.getElementById(chartName).getContext("2d");

  if (oldChart) {
    oldChart.destroy();
  }

  const annotations = {};

  if (reachingTimes.length > 0) {
    for (let i = 0; i < reachingTimes.length; i++) {
      annotations[`reach${i}`] = createVerticalLineAnnotation(
        "Reach",
        "orange",
        reachingTimes[i]
      );
    }
  }

  if (outTimes.length > 0) {
    for (let i = 0; i < outTimes.length; i++) {
      annotations[`out${i}`] = createVerticalLineAnnotation(
        "Out",
        "red",
        outTimes[i]
      );
    }
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
    "green",
    clickUpTime 
  );
}


  return new Chart(ctx, {
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

async function saveTrialToFirestore(trial) {
  try {

    const user = firebase.auth().currentUser;
    if (!user) throw new Error("Usuario no autenticado");


    await db.collection("fitts_trials").add({
      participantId,
      timestamp: new Date().toISOString(),
      ...trial
    });
    console.log("Trial guardado en Firestore");
  } catch (error) {
    console.error("Error al guardar en Firestore:", error);
  }
}


async function initializeParticipant() {
  try {
    const user = firebase.auth().currentUser;
    if (!user) throw new Error("Usuario no autenticado");

    // participantId = user.uid;

    // Genera un número aleatorio entre 0 y feedbackConditions.length - 1
    let orderIndex = Math.floor(Math.random() * feedbackConditions.length);

    feedbackConditions = generateConditions(orderIndex);
    currentCondition  = 0; // Reiniciar al primer índice

    
    // Obtén resolución y zoom
    const screenWidth = window.screen.width;
    const screenHeight = window.screen.height;
    const zoom = window.devicePixelRatio;

    await db.collection("participants").doc(participantId).set({
      startedAt: new Date().toISOString(),
      completed: false,
      orderIndex: orderIndex,
      feedbackConditions : feedbackConditions,
      screenWidth: screenWidth,
      screenHeight: screenHeight,
      zoom: zoom

    });

    console.log("Participante inicializado:", participantId, "orderIndex:", window.orderIndex);
  } catch (err) {
    console.error("Error creando participante:", err);
  }
}