
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

// Function to get Prolific return URL
function getProlificReturnUrl() {
  const params = getProlificParams();
  if (params.studyId && params.sessionId) {
    return `https://app.prolific.com/submissions/complete?cc=C1BLMG3C`;
  }
  return null;
}

// Get Prolific parameters
const prolificParams = getProlificParams();
console.log('Prolific parameters:', prolificParams);


// Pariticipant ID
let participantId = prolificParams.prolificPid || crypto.randomUUID();

let record_results = true; // True if results should be recorded

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


let trackingStartTime = null;

let currentMousePosition = {
    x: 0,
    y: 0,
    time: 0
};


  // UI elemen// UI elements
  const canvas = document.getElementById("experimentCanvas");
  const ctx = canvas.getContext("2d");
  const startButton = {
    x: canvas.width / 2,
    y: canvas.height / 3,
    radius: 50,
    reached: false
  };

currentTrialData = {}
resetCurrentTrialData();

function resetCurrentTrialData() {  
  currentTrialData = {
    feedbackMode: null, // Current feedback mode
    buffer: 0, // Current buffer size
    indication: null, // Current indication method
    cursorPositions: [], // All cursor positions during the trial
    cursorPositionsInterval: [], // Cursor positions sampled at intervals -- JFGA not used, probably remove
    movementStartTime: null, // Time when movement started
    bufferReachingTimes: [], // Times when entering buffer
    bufferOutTimes: [], // Times when exiting buffer
    reachingTimes: [], // Times when entering target
    outTimes: [], // Times when exiting target
    inTarget: false, // Whether currently in target
    inTargetBuffer: false, // Whether currently in buffer 
    success: false, // Cursor in target either at indication down or up,
    sucessUp: false, // Cursor in target at indication up
    sucessDown: false, // Cursor in target at indication down
    A: 0,
    W: 0,
    ID: 0,
    trialIndex: 0,
    targetPosition: { x: -1, y: -1 },
    isFirstTrial: false,
    preFirstTargetPosition: { x: -1, y: -1 },
    indicationsDown: [],
    indicationsUp: [],
    wrongIndications: []
  };  
} 


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
    zoomEstimate: window.outerWidth / window.innerWidth,
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






drawStartButton(canvas, ctx, startButton);


canvas.addEventListener("mousemove", (e) => {
    // Solo durante el experimento

    const now = performance.now();
    currentMousePosition = {
      x: e.offsetX,
      y: e.offsetY, 
      time: now  - currentTrialData.movementStartTime
    };
    if (state.UIstate === UI_STATES.SHOWING_INSTRUCTIONS){
      if(state.set.feedbackMode === "green") {
        if(isInsideCircle(currentMousePosition.x, currentMousePosition.y, startButton)) {
          startButton.reached = true;
        }
        else {
          startButton.reached = false;
        }
        drawInstructions(canvas, ctx, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication);
        return;
      }
      else {
        startButton.reached = false;
        return;
      } 
    }
    if (state.UIstate !== UI_STATES.EXPERIMENT_RUNNING && state.UIstate !== UI_STATES.EXPERIMENT_PRE_START ) return; 
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
            currentTrialData.bufferReachingTimes.push({time: pos.time, x: pos.x, y: pos.y});
            }
        if(distance < target.radius){
            if(!currentTrialData.inTarget){
            currentTrialData.inTarget = true;
            currentTrialData.reachingTimes.push({time: pos.time, x: pos.x, y: pos.y});
            } 
        }
    }
    else {
        target.hit = false;
        if(currentTrialData.inTargetBuffer) {
            currentTrialData.inTargetBuffer = false;
            currentTrialData.bufferOutTimes.push({time: pos.time, x: pos.x, y: pos.y});
        }
        if(distance > target.radius  && currentTrialData.inTarget){
          currentTrialData.inTarget = false;
          currentTrialData.outTimes.push({time: pos.time, x: pos.x, y: pos.y});
        }
    }
    draw(state.set.targets, getCurrentTargetIndex(), state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication, false);

}


canvas.addEventListener("click", (e) => {

  const rect = canvas.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top;


  if (state.UIstate === UI_STATES.START_SCREEN) {
    if (isInsideCircle(clickX, clickY, startButton)) {
        startExperiment();
        state.UIstate = UI_STATES.SHOWING_INSTRUCTIONS;
        drawInstructions(canvas, ctx, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication);
    }
    return;
  }
  else if (state.UIstate === UI_STATES.SHOWING_INSTRUCTIONS) {
    if (state.set.indication === "click") {

      if (isInsideCircle(clickX, clickY, startButton)) {
          pressStartButton();
      }
    }
  }
 
});


function pressStartButton() {

  state.UIstate = UI_STATES.EXPERIMENT_PRE_START;
  const { A, W } = state.experiment.blocks[state.experiment.currentBlock];
  generateRingTargets(A, W);

  resetCurrentTrialData();
  currentTrialData.feedbackMode = state.set.feedbackMode; 
  currentTrialData.buffer = state.set.buffer;
  currentTrialData.indication = state.set.indication;
  currentTrialData.preFirstTargetPosition = { x: startButton.x, y: startButton.y };
  trackingStartTime = performance.now();
  currentTrialData.movementStartTime = trackingStartTime;
  draw(state.set.targets, getCurrentTargetIndex(), state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication, true);
}




function isInsideCircle(x, y, circle) {
  const dx = x - circle.x;
  const dy = y - circle.y;
  return Math.sqrt(dx * dx + dy * dy) <= circle.radius;
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
    

}


function isInExperimentRunningState() {
  return state.UIstate === UI_STATES.EXPERIMENT_RUNNING || state.UIstate === UI_STATES.EXPERIMENT_PRE_START;
}

canvas.addEventListener("mousedown", (e) => {
    if(!isInExperimentRunningState()) return;
    currentMousePosition = {
      x: e.offsetX,
      y: e.offsetY, 
      time: performance.now() - currentTrialData.movementStartTime
    };
    currentTrialData.cursorPositions.push(currentMousePosition);
    if(state.experiment.feedbackConditions[state.experiment.currentCondition].indication === "click") {
        indicationDown();
    } 
    else {
        currentTrialData.wrongIndications.push({ 
            x: currentMousePosition.x,
            y: currentMousePosition.y,
            time: performance.now() -currentTrialData.movementStartTime
        });
    }
});
document.addEventListener("keydown", function(e) {
  
    if(!isInExperimentRunningState() && !(state.UIstate === UI_STATES.SHOWING_INSTRUCTIONS)) return;
    if (e.code === "Space" || e.key === " " || e.key === "Spacebar") {
        if(state.UIstate === UI_STATES.SHOWING_INSTRUCTIONS && state.set.indication === "barspace") {
          let clickX = currentMousePosition.x ;
          let clickY = currentMousePosition.y ;
          if (isInsideCircle(clickX, clickY, startButton)) {
              pressStartButton();
          }
          return;
        }
        if(state.experiment.feedbackConditions[state.experiment.currentCondition].indication === "barspace") {
            indicationDown();
        }
    }
    else {
        currentTrialData.wrongIndications.push({ 
            x: currentMousePosition.x,
            y: currentMousePosition.y,
            time: performance.now() -currentTrialData.movementStartTime
        });
    }
});

function indicationDown() {
    if(!isInExperimentRunningState()) return;
    currentTrialData.indicationsDown.push({ 
          isValid: isValidIndication(),
          inTarget: inTargetReached(), 
          time: performance.now() -currentTrialData.movementStartTime,
          x: currentMousePosition.x,
          y: currentMousePosition.y
      });  
}


canvas.addEventListener("mouseup", (e) => {
    if(!isInExperimentRunningState()) return;
    if(currentTrialData.indicationsDown.length === 0) return; // No ha habido un indicationDown previo
    currentMousePosition = {
      x: e.offsetX,
      y: e.offsetY, 
      time: performance.now() - currentTrialData.movementStartTime
    };
    currentTrialData.cursorPositions.push(currentMousePosition);
    if(state.experiment.feedbackConditions[state.experiment.currentCondition].indication === "click") {
        indicationUp();
    }
});

document.addEventListener("keyup", function(e) {
    if(currentTrialData.indicationsDown.length === 0) return; // No ha habido un indicationDown previo
    if (e.code === "Space" || e.key === " " || e.key === "Spacebar") {
        if(state.experiment.feedbackConditions[state.experiment.currentCondition].indication === "barspace") {
            indicationUp();
        }
    }
});


function getDistanceCursorFromTarget() {
    const dx = currentMousePosition.x - getCurrentTarget().x;
    const dy = currentMousePosition.y - getCurrentTarget().y;
    return Math.sqrt(dx * dx + dy * dy);
}

function inTargetReached() {
    const distance = getDistanceCursorFromTarget();
    return distance <= getCurrentTarget().radius;
}

function isValidIndication() {
    const distance = getDistanceCursorFromTarget();
    const minThreshold = 40; // píxeles mínimos de tolerancia
    const threshold = Math.max(getCurrentTarget().radius * 3, minThreshold);
    return distance < threshold ;
}

function indicationUp() {

  if(!isInExperimentRunningState()) return;

  currentTrialData.indicationsUp.push({ 
        isValid: isValidIndication(),
        inTarget: inTargetReached(), 
        time: performance.now() - currentTrialData.movementStartTime,
        x: currentMousePosition.x,
        y: currentMousePosition.y
    });  

  const lastDown = currentTrialData.indicationsDown[currentTrialData.indicationsDown.length -1];
  const lastUp = currentTrialData.indicationsUp[currentTrialData.indicationsUp.length -1];

  if(!lastDown.isValid && !lastUp.isValid) {
    return; // if both of the indications are not valid, do nothing
  }
  
  currentTrialData.success = false
  currentTrialData.insideBuffer = false;
  if(lastDown.inTarget) {
    let dx = lastDown.x - getCurrentTarget().x;
    let dy = lastDown.y - getCurrentTarget().y; 
    let distance = Math.sqrt(dx * dx + dy * dy);
    if (distance <= getCurrentTarget().radius) {
      currentTrialData.success = true;
      currentTrialData.successDown = true;
    }
    if (distance <= getCurrentTarget().radius + currentTrialData.buffer) {
      currentTrialData.insideBuffer = true;
    }
  }
  if(lastUp.inTarget) {
    let dx = lastUp.x - getCurrentTarget().x;
    let dy = lastUp.y - getCurrentTarget().y; 
    let distance = Math.sqrt(dx * dx + dy * dy);
    if (distance <= getCurrentTarget().radius) {
      currentTrialData.success = true;
      currentTrialData.successUp = true;
    } 
    if (distance <= getCurrentTarget().radius + currentTrialData.buffer) {
      currentTrialData.insideBuffer = true;
    }
  }



  const block = state.experiment.blocks[state.experiment.currentBlock];
  currentTrialData.A = block.A;
  currentTrialData.W = block.W;
  currentTrialData.ID = Math.log2((2 * block.A) / block.W);
  currentTrialData.trialIndex = state.set.currentTrial;
  currentTrialData.targetPosition = { x: getCurrentTarget().x,  y: getCurrentTarget().y };

  if(state.UIstate === UI_STATES.EXPERIMENT_RUNNING) {
      getCurrentTarget().marked = true;
      currentTrialData.isFirstTrial = false;
      if(record_results) saveTrialToFirestore(currentTrialData, state.participant.id);
  }
  else
  {
      currentTrialData.isFirstTrial = true;  
      if(record_results) savePreTrialToFirestore(currentTrialData, state.participant.id);
      state.UIstate = UI_STATES.EXPERIMENT_RUNNING;
  }


  resetCurrentTrialData();
  currentTrialData.feedbackMode = state.set.feedbackMode;
  currentTrialData.buffer = state.set.buffer;
  currentTrialData.indication = state.set.indication;
  trackingStartTime = performance.now();
  currentTrialData.movementStartTime = trackingStartTime;
  nextTrial();
}



async function endExperiment() {
  state.UIstate = UI_STATES.EXPERIMENT_FINISHED;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "24px Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.fillText("You finished... thanks!", canvas.width / 2, canvas.height / 2);
  if(prolificParams.prolificPid) setTimeout(() => { window.location.href = getProlificReturnUrl(); }, 3000);
  //document.getElementById("velocityChart").style.display = "block";
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
    currentTrialData.preFirstTargetPosition = { x: getCurrentTarget().x, y: getCurrentTarget().y };
    const { A, W, feedbackMode, buffer, indication } = state.experiment.blocks[state.experiment.currentBlock];
    generateRingTargets(A, W);
  }


  draw(state.set.targets, getCurrentTargetIndex(), currentTrialData.feedbackMode, currentTrialData.indication, state.UIstate === UI_STATES.EXPERIMENT_PRE_START);

  
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
    startButton.reached = false;
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
      hit: false,
      marked: false
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






// Chart variables -- outdater with the new trial structure
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
