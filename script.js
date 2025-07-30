
// Pariticipant ID
let participantId = crypto.randomUUID();

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
    if (state.UIstate !== 4) return; // Solo durante el experimento

    const now = performance.now();
    if (trackingStartTime && now - trackingStartTime > 6000) return;
    currentMousePosition = {
      x: e.offsetX,
      y: e.offsetY, 
      time: now
    };
    
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
        if(!currentTrialData.inTarget){
          currentTrialData.inTarget = true;
          currentTrialData.reachingTimes.push(pos.time - currentTrialData.movementStartTime);
        } 
    }
    else {
        target.hit = false;
        if(currentTrialData.inTarget){
          currentTrialData.inTarget = false;
          currentTrialData.outTimes.push(pos.time - currentTrialData.movementStartTime);
        }
    }
    draw(state.set.targets, state.set.currentTrial, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication, false);

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
    state.UIstate = 2; // Cambiar estado a experiment running pre start
    draw(state.set.targets, state.set.currentTrial, state.experiment.feedbackConditions[state.experiment.currentCondition].feedbackMode, state.experiment.feedbackConditions[state.experiment.currentCondition].indication, true);
  }
 
});


function isInsideCircle(x, y, circle) {
  const dx = x - circle.x;
  const dy = y - circle.y;
  return Math.sqrt(dx * dx + dy * dy) <= circle.radius;
}


async function startExperiment() {

    state.UIstate = 1; // Presenting instructions
  
    
    randomStart = Math.floor(Math.random() * 10);

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
  return state.UIstate === 3 || state.UIstate === 4;
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
    if(!isInExperimentRunningState()) return;
    if(state.UIstate !== 3) return; //Only durine experiment
    currentTrialData.clickDownTime = performance.now();
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
    if(state.UIstate == 4) { //Only during experiment
        
        currentTrialData.clickUpTime = performance.now();
        const dx = currentMousePosition.x - getCurrentTarget().x;
        const dy = currentMousePosition.y - getCurrentTarget().y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        currentTrialData.success = distance <= getCurrentTarget().radius;
        currentTrialData.insideBuffer = distance <= (getCurrentTarget().radius + state.set.buffer);
        const block = blocks[currentBlock];
        currentTrialData.A = block.A;
        currentTrialData.W = block.W;
        currentTrialData.ID = Math.log2((2 * block.A) / block.W);
        currentTrialData.clickUpTime = currentTrialData.clickUpTime - currentTrialData.movementStartTime;
        currentTrialData.clickDownTime = currentTrialData.clickDownTime - currentTrialData.movementStartTime;
        currentTrialData.confirmationTime = currentTrialData.clickUpTime;
        trialData.push(currentTrialData);
        showTrialData(currentTrialData);
        saveTrialToFirestore(currentTrialData);
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

function generateBlocks() {

    state.experiment.blocks = [];

    currentFeedback = state.experiment.feedbackConditions[state.experiment.currentCondition];
    currentBuffer = currentFeedback.buffer;
    currentFeedbackMode = currentFeedback.feedbackMode;

    for (let A of amplitudes) {
        for (let W of widths) {
        state.experiment.blocks.push({ A, W, feedbackMode: currentFeedbackMode, buffer: currentBuffer, indication: currentFeedback.indication });
        }
    }
    state.experiment.blocks = shuffleArray(state.experiment.blocks);
    state.set.feedbackMode = currentFeedbackMode;
    state.set.buffer = currentBuffer; // Usar el primer buffer como valor por defecto
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