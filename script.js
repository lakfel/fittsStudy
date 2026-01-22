
// UI State constants
const UI_STATES = {
  START_SCREEN: 'START_SCREEN',
  SHOWING_INSTRUCTIONS: 'SHOWING_INSTRUCTIONS',
  EXPERIMENT_PRE_START: 'EXPERIMENT_PRE_START',
  EXPERIMENT_RUNNING: 'EXPERIMENT_RUNNING',
  EXPERIMENT_FINISHED: 'EXPERIMENT_FINISHED'
};

// Function to get URL parameters from Prolific
function getProlificParams() {
  const urlParams = new URLSearchParams(window.location.search);
  return {
    sessionId: urlParams.get('SESSION_ID') || null,
    studyId: urlParams.get('STUDY_ID') || null,
    prolificPid: urlParams.get('PROLIFIC_PID') || null
  };
}

// Function to detect if user is likely using a trackpad
function detectTrackpad() {
  return new Promise((resolve) => {
    let detectionCount = 0;
    let trackpadCount = 0;
    let mouseCount = 0;
    const minSamples = 3; // Necesitamos al menos 3 eventos de scroll para confirmar
    
    const wheelHandler = (e) => {
      let isTrackpad = false;
      
      // Método 1: Comparar wheelDeltaY con deltaY
      if (e.wheelDeltaY) {
        if (e.wheelDeltaY === (e.deltaY * -3)) {
          isTrackpad = true;
        }
      }
      // Método 2: Verificar deltaMode (0 = píxeles, típico de trackpad)
      else if (e.deltaMode === 0) {
        isTrackpad = true;
      }
      
      detectionCount++;
      if (isTrackpad) {
        trackpadCount++;
      } else {
        mouseCount++;
      }
      
      console.log(`Detection ${detectionCount}: ${isTrackpad ? 'Trackpad' : 'Mouse'} (Trackpad: ${trackpadCount}, Mouse: ${mouseCount})`);
      
      // Después de varios eventos, tomar decisión
      if (detectionCount >= minSamples) {
        cleanup();
        const result = trackpadCount > mouseCount;
        console.log(`Final result: ${result ? 'Trackpad' : 'Mouse'} detected (${trackpadCount}/${detectionCount} trackpad events)`);
        resolve(result);
      }
    };
    
    const cleanup = () => {
      document.removeEventListener('wheel', wheelHandler);
      document.removeEventListener('mousewheel', wheelHandler);
      document.removeEventListener('DOMMouseScroll', wheelHandler);
    };
    
    // Escuchar múltiples tipos de eventos de scroll para compatibilidad
    document.addEventListener('wheel', wheelHandler, { passive: true });
    document.addEventListener('mousewheel', wheelHandler, { passive: true });
    document.addEventListener('DOMMouseScroll', wheelHandler, { passive: true });
    
    // Timeout de 8 segundos - si no hay scroll, asumir mouse
    setTimeout(() => {
      if (detectionCount < minSamples) {
        cleanup();
        console.log('Timeout: Not enough scroll events, defaulting to mouse');
        resolve(false);
      }
    }, 8000);
  });
}

// Analizar patrón de movimiento para detectar trackpad
function analyzeMovementPattern(samples, hasTouch) {
  if (samples.length < 5) return false;
  
  // Calcular características del movimiento
  let avgSpeed = 0;
  let speedVariance = 0;
  let smallMovements = 0;
  let totalDistance = 0;
  
  for (let i = 1; i < samples.length; i++) {
    avgSpeed += samples[i].speed;
    totalDistance += samples[i].distance;
    
    // Trackpads tienen muchos movimientos pequeños
    if (samples[i].distance < 2 && samples[i].dt < 20) {
      smallMovements++;
    }
  }
  
  avgSpeed /= (samples.length - 1);
  
  // Calcular varianza de velocidad
  for (let i = 1; i < samples.length; i++) {
    speedVariance += Math.pow(samples[i].speed - avgSpeed, 2);
  }
  speedVariance /= (samples.length - 1);
  
  const stdDev = Math.sqrt(speedVariance);
  const coefficientOfVariation = avgSpeed > 0 ? stdDev / avgSpeed : 0;
  const smallMovementRatio = smallMovements / (samples.length - 1);
  
  console.log('Movement analysis:', {
    avgSpeed,
    stdDev,
    coefficientOfVariation,
    smallMovementRatio,
    totalDistance,
    hasTouch
  });
  
  // Trackpads típicamente tienen:
  // - Mayor proporción de movimientos pequeños (> 0.3)
  // - Movimiento más suave (menor coeficiente de variación < 1.5)
  // - Capacidad táctil en el dispositivo
  
  const trackpadScore = 
    (smallMovementRatio > 0.3 ? 1 : 0) +
    (coefficientOfVariation < 1.5 ? 1 : 0) +
    (hasTouch ? 1 : 0) +
    (totalDistance < 500 ? 1 : 0); // Movimientos más limitados
  
  console.log('Trackpad score:', trackpadScore, '/ 4');
  
  // Si tiene 2 o más indicadores de trackpad, probablemente es trackpad
  return trackpadScore >= 2;
}

// Function to get Prolific return URL
function getProlificReturnUrl() {
  const params = getProlificParams();
  if (params.studyId && params.sessionId) {
    return `https://app.prolific.com/submissions/complete?cc=RETURNED`;
  }
  return null;
}

// Get Prolific parameters
const prolificParams = getProlificParams();
console.log('Prolific parameters:', prolificParams);

// Device detection state
let deviceCheckPassed = false;

// Pariticipant ID
let participantId = prolificParams.prolificPid || crypto.randomUUID();

let record_results = false; // Si se deben guardar los resultados en Firestore

//Experiment variables
const indicationMethods = ["click", "barspace"];


const feedbacks = [
    {feedbackMode : "none",
      buffer: [0]
    }, 
    {feedbackMode : "green",
      buffer: [0, 15]
      //buffer: [0]
    }
];

const amplitudes = [238, 336, 672]; 
const widths = [21, 42, 84];       
/*const amplitudes = [238, 336]; 
const widths = [21, 42];       */
//const trialsPerCombination = 10;
const trialsPerCombination = 10;


let trackingInterval = null;
let currentMousePosition = {
    x: 0,
    y: 0,
    time: 0
};

currentTrialData = {
    feedbackMode: null,
    buffer: 0,
    indication: null,
    cursorPositions: [],
    cursorPositionsInterval: [],
    movementStartTime: null,
    bufferReachingTimes: [],
    bufferOutTimes: [],
    reachingTimes: [],
    outTimes: [],
    inTarget: false,
    inTargetBuffer: false,
    clickDownTime: null,
    clickUpTime: null,
    success: false,
    A: 0,
    W: 0,
    ID: 0,
    trialIndex: 0
};


// Experiment control
let state = {
  experiment: {
    feedbackConditions: [],
    blocks: [],
    currentBlock: 0,
    currentCondition: 0
  },
  participant: {
    id: participantId,
    startedAt: null,
    completed: false,
    orderIndex: null,
    screenWidth: window.screen.width,
    screenHeight: window.screen.height,
    zoom: window.devicePixelRatio,
    feedbackConditions: [],
    // Prolific parameters
    prolificSessionId: prolificParams.sessionId,
    prolificStudyId: prolificParams.studyId,
    prolificPid: prolificParams.prolificPid,
    // Device information
    deviceType: null // Will be set to 'mouse' or 'trackpad'
  },
  set: {
    targets: [],
    currentTrial: 0,
    feedbackMode: null,
    buffer: 0,
    indication: null,
    randomStart: 0,
  },
  UIstate: UI_STATES.START_SCREEN
}




// UI elemen// UI elements
const canvas = document.getElementById("experimentCanvas");
const ctx = canvas.getContext("2d");
const startButton = {
  x: canvas.width / 2,
  y: canvas.height / 2,
  radius: 50,
};


drawStartButton(canvas, ctx, startButton);


canvas.addEventListener("mousemove", (e) => {
    // Solo durante el experimento

    const now = performance.now();
    currentMousePosition = {
      x: e.offsetX,
      y: e.offsetY, 
      time: now  - currentTrialData.movementStartTime
    };
    if (state.UIstate !== UI_STATES.EXPERIMENT_RUNNING) return; 
    if (trackingStartTime && now - trackingStartTime > 6000) return;
    currentTrialData.cursorPositions.push(currentMousePosition);
    checkReaching(currentMousePosition);
});


function checkReaching(pos) {

    const target = getCurrentTarget(); // Alterna entre los targets del par
    const buffer = currentTrialData.buffer || 0; // buffer de colisión
    const dx = pos.x - target.x;
    const dy = pos.y - target.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    
    if (distance < target.radius + buffer) {
        target.hit = true;
        if(!currentTrialData.inTargetBuffer) {
            currentTrialData.inTargetBuffer = true;
            currentTrialData.bufferReachingTimes.push(pos.time);
            }
        if(distance < target.radius){
            if(!currentTrialData.inTarget){
            currentTrialData.inTarget = true;
            currentTrialData.reachingTimes.push(pos.time );
            } 
        }
    }
    else {
        target.hit = false;
        if(currentTrialData.inTargetBuffer) {
            currentTrialData.inTargetBuffer = false;
            currentTrialData.bufferOutTimes.push(pos.time );
        }
        if(distance > target.radius  && currentTrialData.inTarget){
          currentTrialData.inTarget = false;
          currentTrialData.outTimes.push(pos.time );
        }
    }
    draw(state.set.targets, getCurrentTargetIndex(), state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication, false);

}


canvas.addEventListener("click", (e) => {

  const rect = canvas.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top;

  // Handle return button click on trackpad warning screen
  if (window.returnButton && 
      clickX >= window.returnButton.x && 
      clickX <= window.returnButton.x + window.returnButton.width &&
      clickY >= window.returnButton.y && 
      clickY <= window.returnButton.y + window.returnButton.height) {
    if (window.returnButton.url) {
      window.location.href = window.returnButton.url;
    }
    return;
  }

  if (state.UIstate === UI_STATES.START_SCREEN) {
    if (isInsideCircle(clickX, clickY, startButton)) {
        startExperiment();
        state.UIstate = UI_STATES.SHOWING_INSTRUCTIONS;
        drawInstructions(canvas, ctx, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication);
    }
    return;
  }
  else if (state.UIstate === UI_STATES.SHOWING_INSTRUCTIONS) {
    if (isInsideCircle(clickX, clickY, startButton)) {
        state.UIstate = UI_STATES.EXPERIMENT_PRE_START;
        startCursorTracking();
        draw(state.set.targets, getCurrentTargetIndex(), state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication, true);
    }
  }
 
});


function isInsideCircle(x, y, circle) {
  const dx = x - circle.x;
  const dy = y - circle.y;
  return Math.sqrt(dx * dx + dy * dy) <= circle.radius;
}

// Check device and start experiment or show warning
async function checkDeviceAndStart() {
  // Show a temporary message asking user to scroll
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "24px Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.fillText("Please scroll with your mouse wheel...", canvas.width / 2, canvas.height / 2 - 20);
  ctx.font = "18px Arial";
  ctx.fillStyle = "#666";
  ctx.fillText("Scroll up and down a few times", canvas.width / 2, canvas.height / 2 + 20);
  
  const isTrackpad = await detectTrackpad();
  
  // Save device type to state
  state.participant.deviceType = isTrackpad ? 'trackpad' : 'mouse';
  console.log('Device detected:', state.participant.deviceType);
  
  if (isTrackpad && prolificParams.prolificPid) {
    // Show trackpad warning with return button only for Prolific users
    const returnUrl = getProlificReturnUrl();
    drawTrackpadWarning(canvas, ctx, returnUrl);
  } else {
    // Device check passed or not from Prolific, continue normally
    deviceCheckPassed = true;
    startExperiment();
    state.UIstate = UI_STATES.SHOWING_INSTRUCTIONS;
    drawInstructions(canvas, ctx, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication);
  }
}


async function startExperiment() {

    state.UIstate = UI_STATES.SHOWING_INSTRUCTIONS;
  
    state.experiment.currentBlock = 0;
    state.set.currentTrial = 0;
    state.experiment.currentCondition = 0;

    let numberOfConditions = 0;
    for (let feedback of feedbacks) {
      numberOfConditions += feedback.buffer.length;
    }
    numberOfConditions *= indicationMethods.length;

    state.participant.orderIndex = Math.floor(Math.random() * numberOfConditions);
    state.experiment.feedbackConditions = generateConditions(state.participant.orderIndex);
    state.participant.feedbackConditions = state.experiment.feedbackConditions;

    if(record_results) await initializeParticipant(state.participant);
    generateBlocks();
    const { A, W } = state.experiment.blocks[0];
    generateRingTargets(A, W);
    //draw();
   //startCursorTracking();  
}


function isInExperimentRunningState() {
  return state.UIstate === UI_STATES.EXPERIMENT_RUNNING || state.UIstate === UI_STATES.EXPERIMENT_PRE_START;
}

canvas.addEventListener("mousedown", (e) => {
    if(!isInExperimentRunningState()) return;
    if(state.experiment.feedbackConditions[state.experiment.currentCondition].indication === "click") {
        indicationDown();
    }
});
document.addEventListener("keydown", function(e) {
    if(!isInExperimentRunningState()) return;
    if (e.code === "Space" || e.key === " " || e.key === "Spacebar") {
        if(state.experiment.feedbackConditions[state.experiment.currentCondition].indication === "barspace") {
            indicationDown();
        }
    }
});
function indicationDown() {
    if(!isInExperimentRunningState()) return;
    currentTrialData.clickDownTime = performance.now() - currentTrialData.movementStartTime;
    trackingStartTime = performance.now();
}


canvas.addEventListener("mouseup", (e) => {
    if(!isInExperimentRunningState()) return;
    if(state.experiment.feedbackConditions[state.experiment.currentCondition].indication === "click") {
        indicationUp();
    }
});

document.addEventListener("keyup", function(e) {
    if (e.code === "Space" || e.key === " " || e.key === "Spacebar") {
        if(state.experiment.feedbackConditions[state.experiment.currentCondition].indication === "barspace") {
            indicationUp();
        }
    }
});


function indicationUp() {

    if(!isInExperimentRunningState()) return;
    const dx = currentMousePosition.x - getCurrentTarget().x;
    const dy = currentMousePosition.y - getCurrentTarget().y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const minThreshold = 40; // píxeles mínimos de tolerancia
    const threshold = Math.max(getCurrentTarget().radius * 3, minThreshold);
    if(distance >= threshold) return; // No hacer nada si el cursor está muy lejos del target

    if(state.UIstate === UI_STATES.EXPERIMENT_RUNNING) {
        
        currentTrialData.clickUpTime = performance.now() - currentTrialData.movementStartTime;
        
        currentTrialData.success = distance <= getCurrentTarget().radius;
        currentTrialData.insideBuffer = distance <= (getCurrentTarget().radius + state.set.buffer);
        const block = state.experiment.blocks[state.experiment.currentBlock];
        currentTrialData.A = block.A;
        currentTrialData.W = block.W;
        currentTrialData.ID = Math.log2((2 * block.A) / block.W);
        
        currentTrialData.confirmationTime = currentTrialData.clickUpTime;
        currentTrialData.trialIndex = state.set.currentTrial;

        
        //showTrialData(currentTrialData);

        if(record_results) saveTrialToFirestore(currentTrialData, state.participant.id);
    }
    else
    {
        if(distance <= getCurrentTarget().radius) {
            state.UIstate = UI_STATES.EXPERIMENT_RUNNING;
        }
        else{
            return;
        }
    }


      /*   if(firstTrial) {
    firstTrial = false;
    state.set.currentTrial++; // Avanzar al siguiente trial
    draw(); // Redibujar para el siguiente trial
    return; // No hacer nada en el primer click
  }*/
  //const dx = e.offsetX - getCurrentTarget().x;
  //const dy = e.offsetY - getCurrentTarget().y;


  currentTrialData = {
    feedbackMode: state.set.feedbackMode,
    buffer: state.set.buffer,
    indication: state.set.indication,
    cursorPositions: [],
    cursorPositionsInterval: [],
    movementStartTime: null,
    reachingTimes: [],
    outTimes: [],
    bufferReachingTimes: [],
    bufferOutTimes: [],
    inTarget: false,
    inTargetBuffer: false,
    clickDownTime: null,
    clickUpTime: null,
    success: false,
    insideBuffer: false,
    A: 0,
    W: 0,
    ID: 0,
    trialIndex: 0
  };



  nextTrial();
  

}



async function endExperiment() {
  state.UIstate = UI_STATES.EXPERIMENT_FINISHED;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "24px Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.fillText("You finished... thanks!", canvas.width / 2, canvas.height / 2);
  document.getElementById("velocityChart").style.display = "block";
  try {

    if(record_results) completeParticipant(state.participant.id);

  } catch (err) {
    console.error("Error al actualizar participante:", err);
  }
}


function nextTrial() {

 
  state.set.currentTrial++;

  if (state.set.currentTrial >= trialsPerCombination) { // Set finished
    state.UIstate = UI_STATES.EXPERIMENT_PRE_START;
    state.experiment.currentBlock++; // Move to the next Block
    state.set.currentTrial = 0;
    if (state.experiment.currentBlock >= state.experiment.blocks.length) {
      state.experiment.currentBlock = 0;
      state.experiment.currentCondition++; // Move to the next Condition
      if (state.experiment.currentCondition >= state.experiment.feedbackConditions.length) {
        endExperiment();
        return;
      }
      generateBlocks();
      state.UIstate = UI_STATES.SHOWING_INSTRUCTIONS;
      drawInstructions(canvas, ctx, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication);
      return;
    }
    const { A, W, feedbackMode, buffer, indication } = state.experiment.blocks[state.experiment.currentBlock];

    generateRingTargets(A, W);
  }

  stopCursorTracking();
  draw(state.set.targets, getCurrentTargetIndex(), currentTrialData.feedbackMode, currentTrialData.indication, state.UIstate === UI_STATES.EXPERIMENT_PRE_START);

  startCursorTracking();
}


function generateBlocks() {

    state.experiment.blocks = [];

    currentFeedback = state.experiment.feedbackConditions[state.experiment.currentCondition];
    currentBuffer = currentFeedback.buffer;
    currentFeedbackMode = currentFeedback.feedbackMode;
    currentIndication = currentFeedback.indication;


    for (let A of amplitudes) {
        for (let W of widths) {
        state.experiment.blocks.push({ A, W, feedbackMode: currentFeedbackMode, buffer: currentBuffer, indication: currentFeedback.indication });
        }
    }
    state.experiment.blocks = shuffleArray(state.experiment.blocks);

    state.set.feedbackMode = currentFeedbackMode;
    state.set.buffer = currentBuffer;
    state.set.indication = currentIndication;
}


function generateRingTargets(A, W) {

  const N = 9;
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const angleStep = (2 * Math.PI) / N;


  const k = Math.floor(N / 2);
  const angleToOpposite = (2 * Math.PI * k) / N;
  const R = A / (2 * Math.sin(angleToOpposite / 2)); // fórmula clave

  state.set.targets = [];

  for (let i = 0; i < N; i++) {
    const angle = i * angleStep;
    const x = centerX + R * Math.cos(angle);
    const y = centerY + R * Math.sin(angle);

    state.set.targets.push({
      x,
      y,
      radius: W / 2,
    });
  }
  randomStart = Math.floor(Math.random() * 10);
  // Empezar alternancia en 0 y 5 (opuestos)
}


function getCurrentTargetIndex() {
  return (state.set.currentTrial + randomStart) * 5 % 9; // Alterna entre los targets del par
}

function getCurrentTarget() {
  return state.set.targets[getCurrentTargetIndex()]; // Alterna entre los targets del par
}


function generateConditions(orderIndex) {
  feedbackConditions = [];
  let indicationConditions = shuffleArray(indicationMethods);
  for (let i = 0; i < indicationConditions.length; i++) {
    const indication = indicationConditions[i];
    for (let feedback of feedbacks) {
      for (let buf of feedback.buffer) {
        feedbackConditions.push({ feedbackMode: feedback.feedbackMode, buffer: buf, indication: indication });
      }
    }
  }

  const N = feedbackConditions.length;
  feedbackConditions = [...Array(N)].map((_, i) => feedbackConditions[(i + orderIndex) % N]);

  return feedbackConditions;

}

function shuffleArray(array) {
  return array
    .map(value => ({ value, sort: Math.random() }))
    .sort((a, b) => a.sort - b.sort)
    .map(({ value }) => value);
}

function stopCursorTracking() {
  if (trackingInterval) {
    clearInterval(trackingInterval);
    trackingInterval = null;
  }
}


function startCursorTracking() {
  const now = performance.now();

  currentTrialData.movementStartTime = now;
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

    //currentTrialData.cursorPositionsInterval.push(pos);
    //checkReaching(pos);
  }, 2); // cada 10 ms
}


function showTrialData(trial) {
  const infoEl = document.getElementById("trialInfo");
  
  const lastReachingTime = trial.reachingTimes.length > 0 ? trial.reachingTimes[trial.reachingTimes.length - 1] : null;
  const lastOutTime = trial.outTimes.length > 0 ? trial.outTimes[trial.outTimes.length - 1] : null;

  // Mostrar tiempos en números
  const lines = [
    `Feedback: ${currentTrialData.feedbackMode}`,
    `A: ${currentTrialData.A}`,
    `W: ${currentTrialData.W}`,
    `ID: ${currentTrialData.ID.toFixed(2)}`,
    `Reaching Time: ${lastReachingTime?.toFixed(2)} ms`,
    `Out Time: ${lastOutTime?.toFixed(2)} ms`,
    `Confirmation Time: ${currentTrialData.confirmationTime?.toFixed(2)} ms`,
    `Click Duration: ${currentTrialData.clickDuration?.toFixed(2)} ms`,
    `Success: ${currentTrialData.success ? "✔️" : "❌"}`
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
