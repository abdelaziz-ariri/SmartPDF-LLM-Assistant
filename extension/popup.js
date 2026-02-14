let currentQuiz = null;
let userAnswers = [];
let quizSubmitted = false;
let currentFlashcards = [];
let currentPDF = null;

// Variables pour suivre l'état des chargements
let isLoadingSummary = false;
let isLoadingQuiz = false;
let isLoadingFlashcards = false;
let isLoadingResources = false;

// Fonction pour afficher une section
function showSection(sectionId) {
    // Cacher toutes les sections d'abord
    const allSections = document.querySelectorAll('.section');
    allSections.forEach(section => {
        section.classList.remove('visible');
    });
    
    // Afficher la section demandée
    const sectionElement = document.getElementById(sectionId + 'Section');
    if (sectionElement) {
        sectionElement.classList.add('visible');
        // Défiler vers la section
        sectionElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Fonction pour cacher une section
function hideSection(sectionId) {
    const sectionElement = document.getElementById(sectionId + 'Section');
    if (sectionElement) {
        sectionElement.classList.remove('visible');
    }
}

// Fonction pour effacer une section
function clearSection(sectionId) {
    switch(sectionId) {
        case 'summary':
            document.getElementById('summary').innerHTML = '';
            hideSection('summary');
            break;
        case 'quiz':
            document.getElementById('quizForm').innerHTML = '';
            document.getElementById('quizResult').innerHTML = '';
            document.getElementById('submitQuizBtn').style.display = 'none';
            hideSection('quiz');
            currentQuiz = null;
            userAnswers = [];
            quizSubmitted = false;
            break;
        case 'flashcards':
            document.getElementById('flashcardsContent').innerHTML = '';
            hideSection('flashcards');
            currentFlashcards = [];
            break;
        case 'resources':
            document.getElementById('resourcesContent').innerHTML = '';
            hideSection('resources');
            break;
    }
}

// Fonction pour initialiser les onglets
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-tab');
            
            // Mettre à jour les onglets actifs
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${tabId}Tab`) {
                    content.classList.add('active');
                }
            });
        });
    });
}

// Fonction pour désactiver les autres boutons pendant le chargement
function setLoadingState(buttonId, isLoading) {
    const buttons = ['summaryBtn', 'quizBtn', 'flashcardsBtn', 'resourcesBtn'];
    const buttonElement = document.getElementById(buttonId);
    
    if (isLoading) {
        buttonElement.disabled = true;
        buttonElement.innerHTML = '⏳ Chargement...';
    } else {
        buttonElement.disabled = false;
        // Restaurer le texte original selon le bouton
        switch(buttonId) {
            case 'summaryBtn':
                buttonElement.innerHTML = '📝 Résumé';
                break;
            case 'quizBtn':
                buttonElement.innerHTML = '❓ Quiz';
                break;
            case 'flashcardsBtn':
                buttonElement.innerHTML = '🗂️ Flashcards';
                break;
            case 'resourcesBtn':
                buttonElement.innerHTML = '📚 Ressources';
                break;
        }
    }
}

// Fonction pour afficher un message d'état
function showStatus(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (element) {
        element.className = 'status-' + type;
        element.innerHTML = message;
        element.style.display = 'block';
    }
}

// Vérifier si un PDF est sélectionné
function checkPDFSelected() {
    const file = document.getElementById("pdfInput").files[0];
    const url = document.getElementById("pdfUrlInput").value.trim();

    // Si ni fichier ni URL → erreur
    if (!file && url === "") {
        alert("⚠️ Veuillez sélectionner un fichier PDF ou saisir une URL !");
        return false;
    }

     return true; // Fichier PDF valide
}
// Générer uniquement le résumé
async function generateSummary() {
    if (!checkPDFSelected()) return;
    const file = document.getElementById("pdfInput").files[0];
    const url = document.getElementById("pdfUrlInput").value.trim();
    const formData = new FormData();
    if(file){
        formData.append("pdf", file);
    }
    if(url){
        formData.append("url", url);
    }
    setLoadingState('summaryBtn', true);
    isLoadingSummary = true;
    
    // Afficher la section et montrer un indicateur de chargement
    showSection('summary');
    document.getElementById("summary").innerHTML = '<div class="loading">⏳ Génération du résumé en cours...</div>';
    
    try {
        const response = await fetch("http://localhost:5000/generate_summary", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Erreur serveur: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            document.getElementById("summary").innerHTML = `<div class="error">❌ ${data.error}</div>`;
        } else {
            document.getElementById("summary").innerText = data.summary;
        }
        
    } catch (err) {
        console.error(err);
        document.getElementById("summary").innerHTML = '<div class="error">❌ Erreur: Serveur indisponible. Assurez-vous que le serveur Flask est lancé.</div>';
    } finally {
        setLoadingState('summaryBtn', false);
        isLoadingSummary = false;
    }
}

// Générer uniquement le quiz
async function generateQuiz() {
    if (!checkPDFSelected()) return;

    const file = document.getElementById("pdfInput").files[0];
    const url = document.getElementById("pdfUrlInput").value.trim();
    const formData = new FormData();
    if(file){
        formData.append("pdf", file);
    }
    if(url){
        formData.append("url", url);
    }
    setLoadingState('quizBtn', true);
    isLoadingQuiz = true;
    

    
    // Afficher la section du quiz
    showSection('quiz');
    document.getElementById("quizForm").innerHTML = '<div class="loading">⏳ Génération du quiz en cours...</div>';
    document.getElementById("submitQuizBtn").style.display = "none";
    document.getElementById("quizResult").innerHTML = "";
    
    userAnswers = [];
    quizSubmitted = false;
    currentQuiz = null;

    try {
        const response = await fetch("http://localhost:5000/generate_quiz", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Erreur serveur: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            document.getElementById("quizForm").innerHTML = `<div class="error">❌ ${data.error}</div>`;
        } else {
            currentQuiz = data.quiz;
            userAnswers = new Array(currentQuiz.length).fill(null);
            displayQuiz(currentQuiz);
        }
        
    } catch (err) {
        console.error(err);
        document.getElementById("quizForm").innerHTML = '<div class="error">❌ Erreur: Serveur indisponible.</div>';
    } finally {
        setLoadingState('quizBtn', false);
        isLoadingQuiz = false;
    }
}

// Générer les flashcards
async function generateFlashcards() {
    if (!checkPDFSelected()) return;
    const file = document.getElementById("pdfInput").files[0];
    const url = document.getElementById("pdfUrlInput").value.trim();
    const formData = new FormData();
    if(file){
        formData.append("pdf", file);
    }
    if(url){
        formData.append("url", url);
    }
    setLoadingState('flashcardsBtn', true);
    isLoadingFlashcards = true;
    
    
    // Afficher la section des flashcards
    showSection('flashcards');
    document.getElementById("flashcardsContent").innerHTML = '<div class="loading">⏳ Génération des flashcards en cours...</div>';
    
    try {
        const response = await fetch("http://localhost:5000/generate_flashcards", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Erreur serveur: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            document.getElementById("flashcardsContent").innerHTML = `<div class="error">❌ ${data.error}</div>`;
        } else {
            currentFlashcards = data.flashcards;
            displayFlashcards(currentFlashcards);
        }
        
    } catch (err) {
        console.error(err);
        document.getElementById("flashcardsContent").innerHTML = '<div class="error">❌ Erreur: Serveur indisponible.</div>';
    } finally {
        setLoadingState('flashcardsBtn', false);
        isLoadingFlashcards = false;
    }
}

// Générer les ressources éducatives
async function generateResources() {
    if (!checkPDFSelected()) return;
    const file = document.getElementById("pdfInput").files[0];
    const url = document.getElementById("pdfUrlInput").value.trim();
    const formData = new FormData();
    if(file){
        formData.append("pdf", file);
    }
    if(url){
        formData.append("url", url);
    }
    
    setLoadingState('resourcesBtn', true);
    isLoadingResources = true;
    
    // Afficher la section des ressources
    showSection('resources');
    document.getElementById("resourcesContent").innerHTML = '<div class="loading">⏳ Génération des ressources en cours...</div>';
    
    try {
        const response = await fetch("http://localhost:5000/generate_educational_resources", {
            method: "POST",
            body: formData
        });
        if (!response.ok) {
            throw new Error(`Erreur serveur: ${response.status}`);
        }
        const data = await response.json();
        
        if (data.error) {
            document.getElementById("resourcesContent").innerHTML = `<div class="error">❌ ${data.error}</div>`;
        } else {
            displayResources(data.resources);
        }
        
    } catch (err) {
        console.error(err);
        document.getElementById("resourcesContent").innerHTML = '<div class="error">❌ Erreur: Serveur indisponible.</div>';
    } finally {
        setLoadingState('resourcesBtn', false);
        isLoadingResources = false;
    }
}

// Afficher les flashcards
function displayFlashcards(flashcards) {
    const container = document.getElementById("flashcardsContent");
    container.innerHTML = '';
    
    if (!flashcards || flashcards.length === 0) {
        container.innerHTML = '<div class="empty-state">Aucune flashcard générée.</div>';
        return;
    }
    
    const title = document.createElement("h4");
    title.textContent = `${flashcards.length} flashcards générées:`;
    title.style.marginBottom = "15px";
    title.style.color = "#9b59b6";
    container.appendChild(title);
    
    flashcards.forEach((card, index) => {
        const flashcardDiv = document.createElement("div");
        flashcardDiv.className = "flashcard";
        flashcardDiv.dataset.index = index;
        
        const rectoDiv = document.createElement("div");
        rectoDiv.className = "flashcard-recto";
        rectoDiv.textContent = `📌 ${card.recto || 'Pas de question'}`;
        rectoDiv.style.cursor = "pointer";
        
        const versoDiv = document.createElement("div");
        versoDiv.className = "flashcard-verso";
        versoDiv.innerHTML = `<strong>Réponse:</strong><br>${card.verso || 'Pas de réponse'}`;
        
        rectoDiv.addEventListener("click", () => {
            const isVisible = versoDiv.style.display === "block";
            versoDiv.style.display = isVisible ? "none" : "block";
        });
        
        flashcardDiv.appendChild(rectoDiv);
        flashcardDiv.appendChild(versoDiv);
        container.appendChild(flashcardDiv);
    });
    
    // Bouton pour montrer/cacher toutes les réponses
    const toggleBtn = document.createElement("button");
    toggleBtn.textContent = "👁️ Montrer toutes les réponses";
    toggleBtn.style.marginTop = "15px";
    toggleBtn.style.padding = "8px 15px";
    toggleBtn.style.backgroundColor = "#9b59b6";
    toggleBtn.style.color = "white";
    toggleBtn.style.border = "none";
    toggleBtn.style.borderRadius = "4px";
    toggleBtn.style.cursor = "pointer";
    
    let allVisible = false;
    toggleBtn.addEventListener("click", () => {
        allVisible = !allVisible;
        const versoDivs = container.querySelectorAll(".flashcard-verso");
        versoDivs.forEach(div => {
            div.style.display = allVisible ? "block" : "none";
        });
        toggleBtn.textContent = allVisible ? "🙈 Cacher toutes les réponses" : "👁️ Montrer toutes les réponses";
    });
    
    container.appendChild(toggleBtn);
}

// Afficher les ressources
function displayResources(resources) {
    const container = document.getElementById("resourcesContent");
    container.innerHTML = '';
    
    if (!resources || resources.length === 0) {
        container.innerHTML = '<div class="empty-state">Aucune ressource générée.</div>';
        return;
    }
    
    const title = document.createElement("h4");
    title.textContent = `${resources.length} ressources éducatives recommandées:`;
    title.style.marginBottom = "15px";
    title.style.color = "#e67e22";
    container.appendChild(title);
    resources.forEach((resource, index) => {
        const resourceDiv = document.createElement("div");
        resourceDiv.className = "resource-item";
        
        const typeSpan = document.createElement("span");
        typeSpan.className = "resource-type";
        typeSpan.textContent = resource.type || "Ressource";
        
        const titleDiv = document.createElement("div");
        titleDiv.className = "resource-title";
        titleDiv.textContent = `${index + 1}. ${resource.title || 'Sans titre'}`;
        
        const descDiv = document.createElement("div");
        descDiv.className = "resource-description";
        descDiv.textContent = resource.description || 'Pas de description';
        
        const whyDiv = document.createElement("div");
        whyDiv.className = "resource-why";
        whyDiv.innerHTML = `<strong>Pourquoi utile:</strong> ${resource.why_useful || 'Ressource utile pour approfondir'}`;
        
        resourceDiv.appendChild(typeSpan);
        resourceDiv.appendChild(titleDiv);
        resourceDiv.appendChild(descDiv);
        resourceDiv.appendChild(whyDiv);
        
        container.appendChild(resourceDiv);
    });
}

// Afficher le quiz
function displayQuiz(quiz) {
    const form = document.getElementById("quizForm");
    form.innerHTML = "";

    quiz.forEach((q, i) => {
        const questionDiv = document.createElement("div");
        questionDiv.className = "question-block";
        questionDiv.dataset.index = i;

        const questionText = document.createElement("p");
        questionText.innerHTML = `<strong>${i + 1}. ${q.question || 'Question non disponible'}</strong>`;
        questionText.style.marginBottom = "15px";
        questionDiv.appendChild(questionText);

        const optionsContainer = document.createElement("div");
        optionsContainer.className = "options-container";
        
        (q.options || ["a) ...", "b) ...", "c) ...", "d) ..."]).forEach((opt, optIndex) => {
            const optionId = `q${i}_opt${optIndex}`;
            
            const label = document.createElement("label");
            label.className = "option-label";
            label.htmlFor = optionId;
            
            const input = document.createElement("input");
            input.type = "radio";
            input.id = optionId;
            input.name = "q" + i;
            input.value = opt;
            input.style.marginRight = "10px";
            
            input.addEventListener("change", () => {
                if (!quizSubmitted) {
                    userAnswers[i] = opt;
                    
                    const questionLabels = questionDiv.querySelectorAll(".option-label");
                    questionLabels.forEach(lbl => {
                        lbl.classList.remove("selected");
                    });
                    
                    label.classList.add("selected");
                    checkAllQuestionsAnswered();
                }
            });

            const optionText = document.createElement("span");
            optionText.textContent = opt;

            label.appendChild(input);
            label.appendChild(optionText);
            optionsContainer.appendChild(label);
        });

        questionDiv.appendChild(optionsContainer);
        form.appendChild(questionDiv);
    });

    document.getElementById("submitQuizBtn").style.display = "block";
    document.getElementById("submitQuizBtn").disabled = true;
}

// Vérifier si toutes les questions sont répondues
function checkAllQuestionsAnswered() {
    if (!currentQuiz) return;
    const allAnswered = userAnswers.every(answer => answer !== null);
    document.getElementById("submitQuizBtn").disabled = !allAnswered;
}

// Soumettre le quiz
document.getElementById("submitQuizBtn").addEventListener("click", (event) => {
    event.preventDefault();
    if (!currentQuiz || quizSubmitted) return;
    
    let score = 0;
    const total = currentQuiz.length;
    
    const allInputs = document.querySelectorAll('#quizForm input[type="radio"]');
    allInputs.forEach(input => input.disabled = true);
    
    currentQuiz.forEach((q, i) => {
        const questionDiv = document.querySelector(`.question-block[data-index="${i}"]`);
        const userAnswer = userAnswers[i];
        const correctAnswer = q.answer || "";
        const isCorrect = userAnswer === correctAnswer;
        
        if (isCorrect) score++;
        
        const labels = questionDiv.querySelectorAll(".option-label");
        labels.forEach(label => {
            const optionText = label.querySelector("span").textContent;
            
            if (optionText === correctAnswer) {
                label.style.borderColor = "#52c41a";
                label.style.backgroundColor = "#f6ffed";
                label.style.color = "#52c41a";
                label.style.fontWeight = "600";
                
                const checkIcon = document.createElement("span");
                checkIcon.textContent = " ✓";
                checkIcon.style.marginLeft = "10px";
                label.querySelector("span").appendChild(checkIcon);
            } else if (optionText === userAnswer && !isCorrect) {
                label.style.borderColor = "#ff4d4f";
                label.style.backgroundColor = "#fff2f0";
                label.style.color = "#ff4d4f";
                label.style.fontWeight = "600";
                
                const crossIcon = document.createElement("span");
                crossIcon.textContent = " ✗";
                crossIcon.style.marginLeft = "10px";
                label.querySelector("span").appendChild(crossIcon);
            }
        });
    });
    
    const percentage = Math.round((score / total) * 100);
    let resultColor, resultMessage;
    
    if (percentage >= 80) resultColor = "#52c41a", resultMessage = "Excellent ! 🎉";
    else if (percentage >= 60) resultColor = "#faad14", resultMessage = "Bon travail ! 👍";
    else if (percentage >= 40) resultColor = "#fa8c16", resultMessage = "Pas mal ! 💪";
    else resultColor = "#ff4d4f", resultMessage = "Continue à t'entraîner ! 📚";
    
    document.getElementById("quizResult").innerHTML = `
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 10px; margin-top: 20px;">
            <h3 style="margin-bottom: 10px; color: ${resultColor};">Résultats du Quiz</h3>
            <div style="font-size: 48px; font-weight: bold; color: ${resultColor}; margin: 15px 0;">${score}/${total}</div>
            <div style="font-size: 24px; color: ${resultColor}; margin-bottom: 10px;">${percentage}%</div>
            <div style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 20px;">${resultMessage}</div>
        </div>
    `;
    
    quizSubmitted = true;
    document.getElementById("submitQuizBtn").disabled = true;
    document.getElementById("submitQuizBtn").textContent = "Quiz soumis";
});

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    console.log("Extension PDF Mentor IA initialisée");
    
    // Initialiser les onglets
    initTabs();
    
    // Ajouter le drag & drop pour les fichiers
    const fileInputContainer = document.getElementById('fileInputContainer');
    const fileInput = document.getElementById('pdfInput');
    
    fileInputContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileInputContainer.classList.add('drag-over');
    });
    
    fileInputContainer.addEventListener('dragleave', () => {
        fileInputContainer.classList.remove('drag-over');
    });
    
    fileInputContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        fileInputContainer.classList.remove('drag-over');
        
        const file = e.dataTransfer.files[0];
        if (file && file.type === 'application/pdf') {
            fileInput.files = e.dataTransfer.files;
            showStatus('urlStatus', '✅ PDF prêt pour traitement', 'success');
        } else {
            showStatus('urlStatus', '❌ Veuillez déposer un fichier PDF valide', 'error');
        }
    });
    
    // Écouter le changement de fichier
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            showStatus('urlStatus', '✅ PDF sélectionné - Prêt à générer du contenu', 'success');
        }
    });
    
    // Associer les boutons d'action
    document.getElementById("summaryBtn").addEventListener("click", generateSummary);
    document.getElementById("quizBtn").addEventListener("click", generateQuiz);
    document.getElementById("flashcardsBtn").addEventListener("click", generateFlashcards);
    document.getElementById("resourcesBtn").addEventListener("click", generateResources);
    
    // Ajouter les événements pour les boutons "Effacer"
    const clearButtons = document.querySelectorAll('.clear-btn');
    clearButtons.forEach(button => {
        button.addEventListener('click', function() {
            const sectionId = this.getAttribute('data-section');
            clearSection(sectionId);
        });
    });
    
    // Initialiser le bouton "Utiliser l'onglet actuel"
    document.getElementById('useCurrentTabBtn').addEventListener('click', async () => {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (tab.url && tab.url.toLowerCase().endsWith('.pdf')) {
                document.getElementById('pdfUrlInput').value = tab.url;
                showStatus('urlStatus', '✅ PDF détecté dans l\'onglet actuel', 'success');
            } else {
                showStatus('urlStatus', '❌ L\'onglet actuel ne contient pas de PDF', 'error');
            }
        } catch (error) {
            console.error("Erreur:", error);
            showStatus('urlStatus', '❌ Impossible d\'accéder à l\'onglet actuel', 'error');
        }
    });
    
    // Bouton de téléchargement par URL
    document.getElementById('fetchUrlBtn').addEventListener('click', async () => {
        const url = document.getElementById('pdfUrlInput').value.trim();
        if (!url) {
            showStatus('urlStatus', '❌ Veuillez entrer une URL', 'error');
            return;
        }
        
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            showStatus('urlStatus', '❌ URL invalide. Doit commencer par http:// ou https://', 'error');
            return;
        }
        
        // Ici vous devriez ajouter la logique pour télécharger le PDF depuis l'URL
        showStatus('urlStatus', '⏳ Cette fonctionnalité est en cours de développement...', 'loading');
    });
});