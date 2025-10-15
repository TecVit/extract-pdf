from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import base64
import pdfplumber
import tempfile
import os
import requests

app = FastAPI(title="PDF IA API")

# ======== MODELOS DE DADOS ======== #
class PDFBase64(BaseModel):
    file_base64: str

class TextInput(BaseModel):
    texto: str

# ======== ROTA 1: EXTRAÇÃO DO PDF ======== #
@app.post("/extract")
def extract_pdf(data: PDFBase64):
    try:
        pdf_bytes = base64.b64decode(data.file_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name

        texto_total = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                texto_total += page.extract_text() or ""

        os.remove(tmp_path)

        return {"texto": texto_total.strip()}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar PDF: {e}")
    

@app.post("/answer")
def generate_answers(data: TextInput):
    try:
        texto = data.texto.strip()
        API_KEY = os.getenv("GEMINI_API_KEY")
        if not API_KEY:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY não configurada")

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": API_KEY
        }

        import re
        texto_limpo = re.sub(r"<[^>]+>", " ", texto).replace("✔", "").replace("⚠", "")
        texto_limpo = re.sub(r"\s+", " ", texto_limpo).strip()

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"Analise o seguinte texto extraído de um PDF e responda suas perguntas de forma clara e objetiva:\n\n{texto_limpo}"
                        }
                    ]
                }
            ]
        }

        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        resp_json = r.json()

        resposta_gerada = resp_json["candidates"][0]["content"]["parts"][0]["text"]

        return {"respostas": [resposta_gerada]}

    except requests.exceptions.HTTPError as http_err:
        raise HTTPException(status_code=r.status_code, detail=f"Erro na API Gemini: {r.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar respostas: {e}")
    
# ======== ROTA DE TESTE ======== #
@app.get("/")
def home():
    return {"status": "online", "msg": "API de leitura e resposta de PDF com IA"}