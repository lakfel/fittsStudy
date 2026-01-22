


let velocityChart = null;
let velocityChart2 = null;


function drawInstructions(canvas, ctx, feedback, indication) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.arc(startButton.x, startButton.y, startButton.radius, 0, Math.PI * 2);
    ctx.fillStyle = "#007BFF";  //dra color azul
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
    "New Set of targets",
    "Feedback : " + feedback,
    "Selection : " + indication
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
    ctx.fillStyle = feedback === "none" ? "#007BFF" : "#28a745";
    ctx.fill();

  
    ctx.font = "16px Arial";
    ctx.fillStyle = "black";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText(`Feedback: ${feedback} `, indicatorX + 20,  indicatorY);
    ctx.fillText(`Selection: ${indication} `, indicatorX + 20,  2* indicatorY);
}


function drawStartButton(canvas, ctx, startButton) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.beginPath();
  ctx.arc(startButton.x, startButton.y, startButton.radius, 0, Math.PI * 2);
  ctx.fillStyle = "#007BFF";  //dra color azul
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
    "Timing does NOT start until you reach the yellow target, you can rest with the yellow target.",
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



function draw(targets, currentIndex, feedbackMode, indication, firstTrial) {

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  targets.forEach((t, index) => {
    ctx.beginPath();
    ctx.arc(t.x, t.y, t.radius, 0, Math.PI * 2);
    
    let color = "gray";

    if(currentIndex === index){
        if(firstTrial){
          color = "yellow"; // amarillo para el primer trial
        }
        else if (t.hit && feedbackMode != "none") {
            color = "#28a745" ; // verde si hit, rojo si no
        }
        else {
            color = "#007BFF"; // azul si no hit
        }
    }

    ctx.fillStyle = color;
    ctx.fill();
  });


   // --- Indicador de feedback en la esquina superior izquierda ---
    const indicatorX = 30;
    const indicatorY = 30;
    const circleRadius = 10;

    // Dibuja círculo
    ctx.beginPath();
    ctx.arc(indicatorX, indicatorY, circleRadius, 0, Math.PI * 2);
    ctx.fillStyle = feedbackMode === "none" ? "#007BFF" : "#28a745";
    ctx.fill();

  
    ctx.font = "16px Arial";
    ctx.fillStyle = "black";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText(`Feedback: ${feedbackMode} `, indicatorX + 20,  indicatorY);
    ctx.fillText(`Selection: ${indication} `, indicatorX + 20,  2* indicatorY);

}
