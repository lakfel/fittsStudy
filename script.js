
// Pariticipant ID
let participantId = crypto.randomUUID();

//Experiment variables
const indicationMethods = ["click", "barspace"];
//const indicationMethods = ["click"];

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
    feedbackConditions: []
  },
  set: {
    targets: [],
    currentTrial: 0,
    feedbackMode: null,
    buffer: 0,
    indication: null,
    randomStart: 0,
  },
  UIstate: 0 // 0: start button, 1: presenting instructions, 2: experiment running pre start, 3: experiment runing, 4: experiment finished
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
    if (state.UIstate !== 3) return; 
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

  if (state.UIstate == 0) {
    if (isInsideCircle(clickX, clickY, startButton)) {
        startExperiment();
        state.UIstate = 1; // Cambiar estado a presentando instrucciones
        drawInstructions(canvas, ctx, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication);
    }
    return;
  }
  else if (state.UIstate == 1) {
    if (isInsideCircle(clickX, clickY, startButton)) {
        state.UIstate = 2; // Cambiar estado a experiment running pre start
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


async function startExperiment() {

    state.UIstate = 1; // Presenting instructions
  
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

    await initializeParticipant(state.participant);
    generateBlocks();
    const { A, W } = state.experiment.blocks[0];
    generateRingTargets(A, W);
    //draw();
   //startCursorTracking();  
}


function isInExperimentRunningState() {
  return state.UIstate === 3 || state.UIstate === 2;
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

    if(state.UIstate == 3) { //Only during experiment
        
        currentTrialData.clickUpTime = performance.now() - currentTrialData.movementStartTime;
        
        currentTrialData.success = distance <= getCurrentTarget().radius;
        currentTrialData.insideBuffer = distance <= (getCurrentTarget().radius + state.set.buffer);
        const block = state.experiment.blocks[state.experiment.currentBlock];
        currentTrialData.A = block.A;
        currentTrialData.W = block.W;
        currentTrialData.ID = Math.log2((2 * block.A) / block.W);
        
        currentTrialData.confirmationTime = currentTrialData.clickUpTime;
        currentTrialData.trialIndex = state.set.currentTrial;
        
        saveTrialToFirestore(currentTrialData, state.participant.id);
    }
    else
    {
        if(distance <= getCurrentTarget().radius) {
            state.UIstate = 3;
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
  state.UIstate = 5; // Done
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "24px Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  ctx.fillText("You finished... thanks!", canvas.width / 2, canvas.height / 2);
  document.getElementById("velocityChart").style.display = "block";
  try {
    
    completeParticipant(state.participant.id);
    
  } catch (err) {
    console.error("Error al actualizar participante:", err);
  }
}


function nextTrial() {

 
  state.set.currentTrial++;

  if (state.set.currentTrial >= trialsPerCombination) { // Set finished
    state.UIstate = 2;
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
      state.UIstate = 1;
      drawInstructions(canvas, ctx, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication);
      return;
    }
    const { A, W, feedbackMode, buffer, indication } = state.experiment.blocks[state.experiment.currentBlock];

    generateRingTargets(A, W);
  }

  stopCursorTracking();
  draw(state.set.targets, getCurrentTargetIndex(), currentTrialData.feedbackMode, currentTrialData.indication, state.UIstate === 2);

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
