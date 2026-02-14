# 📌 SmartPDF-Assistant
**Chrome Extension + Flask Backend for Educational PDF Analysis**  
Interactive summaries, quizzes, and NLP insights from PDF documents using AI to enhance learning and comprehension.

---

## 🛠 Features
- Chrome Extension for user interaction via a popup.
- Flask backend (`app.py`) that:
  - Processes PDF files.
  - Builds prompts for AI analysis.
  - Generates summaries, quizzes, and NLP insights.
- Designed for educational purposes to help students and educators better understand documents.
- Compatible with AI models accessible via the backend.

---

## 📂 Project Structure
```bash
/chrome-extension
    popup.html
    popup.js
    background.js
    styles.css
    manifest.json
/backend
    app.py      # PDF processing + prompt generation
    .env        # configuration variables for backend
```
---

## 🚀 Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-username/SmartPDF-Assistant.git
cd SmartPDF-Assistant 
```

2. **Install backend dependencies**
```bash
# Navigate to backend
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```
---

## Set up the Chrome Extension

Open Chrome → Extensions → Enable Developer Mode → Load unpacked → select the chrome-extension folder.

---
## ⚡Usage
Open the Chrome Extension.
Select a PDF or enter text.
The extension sends the data to app.py via Flask.
app.py processes the document and generates educational insights.
The result (summary, quiz, NLP output) is returned to the user via the extension popup.

---
## 📄 Notes
Intended for academic and educational use.
PDFs should be compatible with the AI models used (size, format, encoding).
The project encourages interactive learning through AI-powered document analysis.
