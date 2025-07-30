
async function saveTrialToFirestore(trial, participantId) {
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


async function initializeParticipant(participant) {
  try {
    const user = firebase.auth().currentUser;
    if (!user) throw new Error("Usuario no autenticado");

    

    await db.collection("participants").doc(participant.id).set({
      startedAt: new Date().toISOString(),
      completed: false,
      orderIndex: participant.orderIndex,
      feedbackConditions: participant.feedbackConditions,
      screenWidth: participant.screenWidth,
      screenHeight: participant.screenHeight,
      zoom: participant.zoom

    });

    console.log("Participante inicializado:", participantId, "orderIndex:", participant.orderIndex);
  } catch (err) {
    console.error("Error creando participante:", err);
  }
}

async function completeParticipant(participantId) {
  try {
    const user = firebase.auth().currentUser;
    if (!user) throw new Error("Usuario no autenticado");

    await db.collection("participants").doc(participantId).update({
        completed: true,
        endedAt: new Date().toISOString()
      });

    console.log("Participante completado:", participantId);
  } catch (err) {
    console.error("Error completando participante:", err);
  }
}