// Écoute les messages du popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "downloadPDF") {
    downloadPDFFromUrl(request.url, sendResponse);
    return true; // Indique que la réponse sera envoyée de manière asynchrone
  }
});

// Fonction pour télécharger un PDF depuis une URL
async function downloadPDFFromUrl(url, sendResponse) {
  try {
    console.log(`Téléchargement du PDF depuis: ${url}`);
    
    // Vérifier que c'est bien un PDF
    if (!url.toLowerCase().endsWith('.pdf') && !url.includes('.pdf?')) {
      sendResponse({ 
        success: false, 
        error: "L'URL ne semble pas pointer vers un fichier PDF" 
      });
      return;
    }

    // Télécharger le PDF
    const response = await fetch(url, {
      mode: 'cors',
      headers: {
        'Accept': 'application/pdf'
      }
    });

    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }

    const blob = await response.blob();
    
    // Créer un FormData pour envoyer au serveur
    const formData = new FormData();
    const file = new File([blob], "online.pdf", { type: "application/pdf" });
    formData.append("pdf", file);
    
    // Envoyer au serveur Flask
    const serverResponse = await fetch("http://localhost:5000/process_pdf", {
      method: "POST",
      body: formData
    });

    const data = await serverResponse.json();
    
    if (serverResponse.ok) {
      sendResponse({ 
        success: true, 
        data: data 
      });
    } else {
      sendResponse({ 
        success: false, 
        error: data.error || "Erreur serveur" 
      });
    }
    
  } catch (error) {
    console.error("Erreur lors du téléchargement:", error);
    sendResponse({ 
      success: false, 
      error: `Erreur: ${error.message}` 
    });
  }
}