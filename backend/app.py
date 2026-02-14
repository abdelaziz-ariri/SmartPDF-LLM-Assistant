
from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import requests
import json
import re
import io
import logging
import os
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Config API Gemini
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
def clean_text_spaces(text):
    """
    Nettoie et corrige les espaces dans le texte extrait.
    """
    if not text:
        return text
    
    # 1. Remplacer les espaces multiples et tabulations par un seul espace
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 2. Ajouter un espace après les ponctuations si manquant
    text = re.sub(r'([.,;:!?])(?=[A-Za-zÀ-ÿ])', r'\1 ', text)
    
    # 3. Corriger les mots collés (minuscule suivie de majuscule)
    text = re.sub(r'([a-zà-ÿ])([A-ZÀ-Ÿ])', r'\1 \2', text)
    
    # 4. Corriger les chiffres collés aux lettres
    text = re.sub(r'(\d)([A-Za-zÀ-ÿ])', r'\1 \2', text)
    text = re.sub(r'([A-Za-zÀ-ÿ])(\d)', r'\1 \2', text)
    
    # 5. Ajouter espace avant parenthèses ouvrantes
    text = re.sub(r'([A-Za-zÀ-ÿ])\(', r'\1 (', text)
    
    # 6. Ajouter espace après parenthèses fermantes (sauf si ponctuation après)
    text = re.sub(r'\)(?=[A-Za-zÀ-ÿ])', ') ', text)
    
    # 7. Conserver les sauts de ligne significatifs
    text = re.sub(r'\.\s+', '.\n', text)
    text = re.sub(r'\?\s+', '?\n', text)
    text = re.sub(r'!\s+', '!\n', text)
    
    # 8. Supprimer les espaces en début/fin de ligne
    text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
    
    # 9. Remplacer les espaces insécables ou spéciaux par des espaces normaux
    text = text.replace('\u00A0', ' ')  # espace insécable
    text = text.replace('\u200B', '')   # espace de largeur nulle
    
    # 10. Final: remplacer les espaces multiples consécutifs par un seul
    text = re.sub(r' +', ' ', text)
    
    return text

def parse_markdown_quiz(markdown_text):
    """Parse le texte Markdown du quiz pour le convertir en structure JSON"""
    quiz_data = []
    
    try:
        if "### Questions" not in markdown_text or "### Corrections" not in markdown_text:
            return None
        
        questions_section = markdown_text.split("### Questions")[1].split("### Corrections")[0]
        corrections_section = markdown_text.split("### Corrections")[1]
        
        questions = []
        question_pattern = r'\*\*(\d+)\.\s*(.+?)\*\*'
        question_matches = list(re.finditer(question_pattern, questions_section, re.DOTALL))
        
        for i, match in enumerate(question_matches):
            question_num = int(match.group(1))
            question_text = match.group(2).strip()
            
            start_pos = match.end()
            if i < len(question_matches) - 1:
                end_pos = question_matches[i + 1].start()
                options_text = questions_section[start_pos:end_pos]
            else:
                options_text = questions_section[start_pos:]
            
            options = []
            option_pattern = r'([a-d])\)\s*(.+?)(?=\n[a-d]\)|\n\n|$)'
            option_matches = re.findall(option_pattern, options_text, re.DOTALL)
            
            for letter, option_text in option_matches:
                options.append(f"{letter}) {option_text.strip()}")
            
            if len(options) != 4:
                while len(options) < 4:
                    options.append("")
            
            questions.append({
                'number': question_num,
                'question': question_text,
                'options': options
            })
        
        corrections = {}
        correction_pattern = r'\*\*(\d+)\.\s*Réponse\s*:\s*([a-d])\)\s*(.+?)\*\*'
        correction_matches = re.findall(correction_pattern, corrections_section, re.DOTALL)
        
        for num, letter, answer_text in correction_matches:
            corrections[int(num)] = {
                'answer_letter': letter,
                'answer_text': answer_text.strip()
            }
        
        explanations = {}
        explanation_pattern = r'\*\*(\d+)\.\s*Réponse\s*:\s*[a-d]\)\s*.+?\*\*\s*\*Explication\s*:\s*(.+?)(?=\n\*\*\d+\.|\n\n|$)'
        explanation_matches = re.findall(explanation_pattern, corrections_section, re.DOTALL)
        
        for num, explanation in explanation_matches:
            explanations[int(num)] = explanation.strip()
        
        for q in questions:
            question_num = q['number']
            correct_option = ""
            
            if question_num in corrections:
                correct_letter = corrections[question_num]['answer_letter']
                for option in q['options']:
                    if option.startswith(f"{correct_letter})"):
                        correct_option = option
                        break
            
            explanation = explanations.get(question_num, "Pas d'explication disponible.")
            
            quiz_data.append({
                'question': q['question'],
                'options': q['options'],
                'answer': correct_option,
                'explanation': explanation
            })
        
        return quiz_data
        
    except Exception as e:
        logger.error(f"Erreur lors du parsing du Markdown: {e}")
        return None

def call_gemini(prompt, is_json=False, max_retries=2):
    """Appelle l'API Gemini avec gestion des erreurs"""
    for attempt in range(max_retries):
        try:
            if is_json:
                system_instruction = """Tu dois répondre UNIQUEMENT avec un objet JSON valide.
                Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire."""
                
                full_prompt = f"{system_instruction}\n\n{prompt}"
            else:
                full_prompt = prompt
            
            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.3,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(BASE_URL, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if "candidates" in result and result["candidates"]:
                    text_response = result["candidates"][0]["content"]["parts"][0]["text"]
                    
                    if is_json:
                        clean_text = text_response.strip()
                        
                        if clean_text.startswith("```json"):
                            clean_text = clean_text[7:]
                        if clean_text.startswith("```"):
                            clean_text = clean_text[3:]
                        if clean_text.endswith("```"):
                            clean_text = clean_text[:-3]
                        clean_text = clean_text.strip()
                        
                        try:
                            return json.loads(clean_text)
                        except json.JSONDecodeError:
                            logger.warning("JSON invalide, tentative de parsing Markdown")
                            parsed = parse_markdown_quiz(clean_text)
                            if parsed:
                                return parsed
                            continue
                    else:
                        return text_response
                        
            else:
                logger.error(f"Erreur API: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Exception lors de l'appel Gemini: {e}")
        
        import time
        time.sleep(1)
    
    return None if is_json else "Erreur: Impossible de générer le contenu."

def extract_text_from_pdf(pdf_file, clean_spaces=True):
    """Extrait le texte d'un PDF avec option de nettoyage des espaces"""
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages[:10]):
                # Utiliser layout=True pour mieux préserver la structure
                page_text = page.extract_text(layout=True)
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            return None, "Le PDF ne contient pas de texte lisible"
        
        # Nettoyer les espaces si demandé
        if clean_spaces:
            text = clean_text_spaces(text)
            
        if len(text) > 6000:
            text = text[:6000] + "\n\n[Texte tronqué pour des raisons de performance]"
            
        return text, None
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction PDF: {e}")
        return None, f"Erreur lors de la lecture du PDF: {str(e)}"

def process_pdf_from_url(url, clean_spaces=True):
    """Télécharge et traite un PDF depuis une URL"""
    try:
        # Valider l'URL
        if not url.startswith(('http://', 'https://')):
            return None, "URL invalide"
        
        # Télécharger le PDF
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        if response.status_code != 200:
            return None, f"Impossible de télécharger le PDF (HTTP {response.status_code})"
        
        # Vérifier que c'est bien un PDF
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
            return None, "Le contenu n'est pas un PDF"
        
        # Lire le PDF depuis les bytes
        pdf_bytes = io.BytesIO(response.content)
        text = ""
        
        with pdfplumber.open(pdf_bytes) as pdf:
            for i, page in enumerate(pdf.pages[:10]):
                # Utiliser layout=True pour mieux préserver la structure
                page_text = page.extract_text(layout=True)
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            return None, "Le PDF ne contient pas de texte lisible"
        
        # Nettoyer les espaces si demandé
        if clean_spaces:
            text = clean_text_spaces(text)
        
        # Limiter la taille du texte
        if len(text) > 6000:
            text = text[:6000] + "\n\n[Texte tronqué pour des raisons de performance]"
        print("OK")
        return text, None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur de téléchargement: {e}")
        return None, f"Erreur de téléchargement: {str(e)}"
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'URL: {e}")
        return None, f"Erreur de traitement: {str(e)}"

def generate_fallback_quiz():
    """Génère un quiz de secours"""
    return [
        {
            "question": "Que signifie l'acronyme PDF ?",
            "options": [
                "a) Portable Document Format",
                "b) Personal Data File", 
                "c) Printable Document Form",
                "d) Public Document File"
            ],
            "answer": "a) Portable Document Format",
            "explanation": "PDF signifie Portable Document Format, un format de fichier développé par Adobe."
        },
        {
            "question": "Quelle est la principale caractéristique d'un fichier PDF ?",
            "options": [
                "a) Il est toujours modifiable",
                "b) Il préserve la mise en forme sur tous les appareils",
                "c) Il est toujours plus petit qu'un fichier Word",
                "d) Il ne peut contenir que du texte"
            ],
            "answer": "b) Il préserve la mise en forme sur tous les appareils",
            "explanation": "Le format PDF préserve la mise en forme originale du document quel que soit l'appareil ou le logiciel utilisé."
        }
    ]

def generate_fallback_flashcards():
    """Génère des flashcards de secours"""
    return [
        {
            "recto": "Que signifie PDF ?",
            "verso": "Portable Document Format - Format de document portable créé par Adobe."
        },
        {
            "recto": "Quel est l'avantage principal du format PDF ?",
            "verso": "Il conserve la mise en forme originale du document sur n'importe quel appareil."
        },
        {
            "recto": "Quel logiciel a créé le format PDF ?",
            "verso": "Adobe Systems a développé le format PDF dans les années 1990."
        }
    ]

def generate_fallback_resources():
    """Génère des ressources de secours"""
    return [
        {
            "type": "Documentation",
            "title": "Guide officiel du format PDF",
            "description": "Documentation complète sur le format PDF par Adobe",
            "why_useful": "Comprendre les spécifications techniques du format PDF"
        },
        {
            "type": "Tutoriel",
            "title": "Créer et manipuler des PDF avec Python",
            "description": "Tutoriel sur l'utilisation de bibliothèques Python pour les PDF",
            "why_useful": "Apprendre à automatiser le traitement des PDF"
        }
    ]

@app.route("/process_pdf", methods=["POST"])
def process_pdf():
    """Traite un PDF envoyé depuis l'extension (fichier ou URL)"""
    try:
        # Vérifier si c'est un fichier uploadé
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file and file.filename != '' and file.filename.lower().endswith('.pdf'):
                return process_uploaded_pdf(file)
        
        # Vérifier si c'est une URL envoyée en JSON
        if request.is_json:
            data = request.get_json()
            if 'url' in data:
                return process_pdf_url_endpoint(data['url'])
        
        return jsonify({"error": "Aucun PDF valide reçu"}), 400
        
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return jsonify({"error": str(e)}), 500

def process_uploaded_pdf(file):
    """Traite un fichier PDF uploadé"""
    try:
        text, error = extract_text_from_pdf(file, clean_spaces=True)
        if error:
            return jsonify({"error": error}), 400
        
        if not text:
            return jsonify({"error": "Impossible d'extraire le texte du PDF"}), 400
        
        return jsonify({
            "success": True,
            "text": text,
            "text_length": len(text),
            "message": "PDF traité avec succès"
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du fichier PDF: {e}")
        return jsonify({"error": f"Erreur de traitement: {str(e)}"}), 500

def process_pdf_url_endpoint(url):
    """Point d'entrée pour traiter un PDF depuis une URL"""
    try:
        text, error = process_pdf_from_url(url, clean_spaces=True)
        if error:
            return jsonify({"error": error}), 400
        
        if not text:
            return jsonify({"error": "Impossible d'extraire le texte du PDF"}), 400
        
        return jsonify({
            "success": True,
            "text": text,
            "text_length": len(text),
            "message": "PDF traité avec succès"
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'URL: {e}")
        return jsonify({"error": f"Erreur de traitement: {str(e)}"}), 500

@app.route("/generate_summary", methods=["POST"])
def generate_summary():
    """Génère uniquement le résumé"""
    try:
        # Cas 1 : PDF Uploadé
        if "pdf" in request.files:
            file = request.files.get("pdf")
            if not file or file.filename == "":
                return jsonify({"error": "Aucun fichier PDF reçu"}), 400

            text, error = extract_text_from_pdf(file, clean_spaces=True)

        # Cas 2 : URL via FormData
        elif "url" in request.form:
            url = request.form.get("url")
            text, error = process_pdf_from_url(url, clean_spaces=True)

        # Cas 3 : JSON (optionnel)
        elif request.is_json:
            data = request.get_json()
            if "url" in data:
                text, error = process_pdf_from_url(data["url"], clean_spaces=True)
            elif "text" in data:
                text = data["text"]
                error = None
            else:
                return jsonify({"error": "Aucun PDF ou URL fourni"}), 400

        else:
            return jsonify({"error": "Aucun fichier ou URL reçu"}), 400

        # Gestion erreurs extraction PDF
        if error:
            return jsonify({"error": error}), 400

        # Construction du prompt
        summary_prompt = f"""
Tu es un expert en synthèse de documents.
Fais un résumé clair, structuré et concis du texte suivant.
Le résumé doit être en français et ne pas dépasser 300 mots.

Texte à résumer:
{text}
"""

        summary = call_gemini(summary_prompt, is_json=False)

        if not summary or summary.startswith("Erreur"):
            summary = "Impossible de générer le résumé. Veuillez réessayer."

        return jsonify({
            "summary": summary,
            "metadata": {
                "text_length": len(text),
                "status": "success"
            }
        })

    except Exception as e:
        logger.error(f"Erreur lors de la génération du résumé: {e}")
        return jsonify({
            "error": f"Erreur lors de la génération du résumé: {str(e)}",
            "summary": "Une erreur est survenue lors de la génération du résumé."
        }), 500

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    """Génère uniquement le quiz"""
    try:
        # ----- Cas 1 : PDF Upload (FormData) -----
        if "pdf" in request.files:
            file = request.files.get("pdf")
            if not file or file.filename == "":
                return jsonify({"error": "Aucun fichier PDF reçu"}), 400

            text, error = extract_text_from_pdf(file, clean_spaces=True)

        # ----- Cas 2 : URL envoyée via FormData -----
        elif "url" in request.form:
            url = request.form.get("url")
            text, error = process_pdf_from_url(url, clean_spaces=True)

        # ----- Cas 3 : Envoi JSON (optionnel) -----
        elif request.is_json:
            data = request.get_json()
            if "url" in data:
                text, error = process_pdf_from_url(data["url"], clean_spaces=True)
            elif "text" in data:
                text = data["text"]
                error = None
            else:
                return jsonify({"error": "Aucun PDF ou URL fourni"}), 400

        else:
            return jsonify({"error": "Aucun fichier ou URL reçu"}), 400

        # ----- Vérification erreurs extraction -----
        if error:
            return jsonify({"error": error}), 400

        # ----- Prompt génération quiz -----
        quiz_prompt = f"""
Tu es un générateur expert de quiz pédagogiques.

Basé sur le texte suivant, génère un quiz de 5 questions à choix multiples.

INSTRUCTIONS:
1. Génère exactement 5 questions.
2. Chaque question doit avoir exactement 4 options.
3. Formate les options ainsi : "a) ...", "b) ...", "c) ...", "d) ...".
4. Indique clairement la bonne réponse : "answer": "a) ...".
5. Ajoute une explication pour chaque bonne réponse.
6. Utilise uniquement les informations contenues dans le texte.
7. Retourne la réponse en JSON valide.

Format attendu:
[
  {{
    "question": "Texte",
    "options": ["a) ...", "b) ...", "c) ...", "d) ..."],
    "answer": "a) ...",
    "explanation": "..."
  }}
]

Texte:
{text}
"""

        quiz_data = call_gemini(quiz_prompt, is_json=True)

        # Si modèle ne renvoie rien → fallback
        if quiz_data is None:
            quiz_data = generate_fallback_quiz()

        return jsonify({
            "quiz": quiz_data,
            "metadata": {
                "text_length": len(text),
                "questions_count": len(quiz_data) if quiz_data else 0,
                "status": "success"
            }
        })

    except Exception as e:
        logger.error(f"Erreur lors de la génération du quiz: {e}")
        return jsonify({
            "error": f"Erreur lors de la génération du quiz: {str(e)}",
            "quiz": generate_fallback_quiz()
        }), 500

@app.route("/generate_flashcards", methods=["POST"])
def generate_flashcards():
    """Génère des flashcards basées sur le PDF ou l’URL"""
    try:
        # ----- Cas 1 : PDF Uploadé (FormData) -----
        if "pdf" in request.files:
            file = request.files.get("pdf")
            if not file or file.filename == "":
                return jsonify({"error": "Aucun fichier PDF reçu"}), 400

            text, error = extract_text_from_pdf(file, clean_spaces=True)

        # ----- Cas 2 : URL envoyée via FormData -----
        elif "url" in request.form:
            url = request.form.get("url")
            text, error = process_pdf_from_url(url, clean_spaces=True)

        # ----- Cas 3 : Envoi JSON (optionnel) -----
        elif request.is_json:
            data = request.get_json()
            if "url" in data:
                text, error = process_pdf_from_url(data["url"], clean_spaces=True)
            elif "text" in data:
                text = data["text"]
                error = None
            else:
                return jsonify({"error": "Aucun PDF ou URL fourni"}), 400
        
        else:
            return jsonify({"error": "Aucun fichier ou URL reçu"}), 400

        # ----- Vérification erreurs extraction -----
        if error:
            return jsonify({"error": error}), 400

        # ----- Prompt génération flashcards -----
        flashcards_prompt = f"""
Tu es un expert pédagogique spécialisé dans la création de flashcards.

Basé sur le texte suivant, génère exactement **10 flashcards éducatives**.

INSTRUCTIONS STRICTES :
1. Génère exactement 10 flashcards.
2. Chaque flashcard doit contenir :
   - "recto": une question ou un concept
   - "verso": la réponse ou l’explication
3. Les flashcards doivent couvrir les concepts les plus importants du texte.
4. Sois clair, concis et pédagogique.
5. Retourne uniquement du JSON valide.

FORMAT EXACT :
[
  {{
    "recto": "Question ou concept",
    "verso": "Réponse ou explication"
  }}
]

Texte :
{text}
"""

        flashcards_data = call_gemini(flashcards_prompt, is_json=True)

        if flashcards_data is None:
            flashcards_data = generate_fallback_flashcards()

        return jsonify({
            "flashcards": flashcards_data,
            "metadata": {
                "text_length": len(text),
                "flashcards_count": len(flashcards_data) if flashcards_data else 0,
                "status": "success"
            }
        })

    except Exception as e:
        logger.error(f"Erreur lors de la génération des flashcards: {e}")
        return jsonify({
            "error": f"Erreur lors de la génération des flashcards: {str(e)}",
            "flashcards": generate_fallback_flashcards()
        }), 500

@app.route("/generate_educational_resources", methods=["POST"])
def generate_educational_resources():
    """Génère des ressources éducatives basées sur le PDF ou l'URL"""
    try:
        # ----- Cas 1 : PDF Uploadé via FormData -----
        if "pdf" in request.files:
            file = request.files.get("pdf")
            if not file or file.filename == "":
                return jsonify({"error": "Aucun fichier PDF reçu"}), 400

            text, error = extract_text_from_pdf(file, clean_spaces=True)

        # ----- Cas 2 : URL envoyée via FormData -----
        elif "url" in request.form:
            url = request.form.get("url")
            text, error = process_pdf_from_url(url, clean_spaces=True)

        # ----- Cas 3 : JSON (optionnel) -----
        elif request.is_json:
            data = request.get_json()
            if "url" in data:
                text, error = process_pdf_from_url(data["url"], clean_spaces=True)
            elif "text" in data:
                text = data["text"]
                error = None
            else:
                return jsonify({"error": "Aucun PDF ou URL fourni"}), 400

        else:
            return jsonify({"error": "Aucun fichier ou URL reçu"}), 400

        # ----- Vérification erreurs extraction -----
        if error:
            return jsonify({"error": error}), 400

        # ----- Prompt -----
        resources_prompt = f"""
Tu es un expert en pédagogie et recommandation de ressources d'apprentissage.

Basé sur le texte suivant, génère **5 à 8 ressources éducatives** pour approfondir le sujet.

INSTRUCTIONS STRICTES :
1. Génère entre 5 et 8 ressources.
2. Pour chaque ressource, fournis :
   - "type": (livre, article, vidéo, cours en ligne, MOOC, documentaire, etc.)
   - "title": titre de la ressource
   - "description": bref résumé (1 à 3 phrases)
   - "why_useful": pourquoi cette ressource est pertinente pour comprendre le sujet
3. Propose des ressources **réelles si possible**, sinon cohérentes.
4. Retourne uniquement un JSON valide.

FORMAT ATTENDU :
[
  {{
    "type": "livre",
    "title": "Titre du livre",
    "description": "Courte description",
    "why_useful": "Raison de pertinence"
  }}
]

Texte :
{text}
"""

        resources_data = call_gemini(resources_prompt, is_json=True)

        if resources_data is None:
            resources_data = generate_fallback_resources()

        return jsonify({
            "resources": resources_data,
            "metadata": {
                "text_length": len(text),
                "resources_count": len(resources_data) if resources_data else 0,
                "status": "success"
            }
        })

    except Exception as e:
        logger.error(f"Erreur lors de la génération des ressources: {e}")
        return jsonify({
            "error": f"Erreur lors de la génération des ressources: {str(e)}",
            "resources": generate_fallback_resources()
        }), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Vérifie que le serveur fonctionne"""
    return jsonify({
        "status": "healthy",
        "service": "PDF Mentor IA",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "process_pdf": "POST /process_pdf (fichier ou URL)",
            "summary": "POST /generate_summary",
            "quiz": "POST /generate_quiz",
            "flashcards": "POST /generate_flashcards",
            "resources": "POST /generate_educational_resources"
        }
    }), 200

if __name__ == "__main__":
    print("=" * 60)
    print("PDF Mentor IA - Serveur Backend")
    print("=" * 60)
    print("Endpoints disponibles:")
    print("1. Process PDF: POST http://localhost:5000/process_pdf (fichier ou URL)")
    print("2. Résumé:     POST http://localhost:5000/generate_summary")
    print("3. Quiz:       POST http://localhost:5000/generate_quiz")
    print("4. Flashcards: POST http://localhost:5000/generate_flashcards")
    print("5. Ressources: POST http://localhost:5000/generate_educational_resources")
    print("6. Santé:      GET  http://localhost:5000/health")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)