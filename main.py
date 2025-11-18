from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import google.generativeai as genai
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# CORS más permisivo para desarrollo
CORS(app, origins=["https://www.abolegal.cl", "http://localhost:3000", "https://*.onrender.com", "http://localhost:*"])

# API key de Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Por favor define GEMINI_API_KEY en las variables de entorno de Render.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

LEGAL_PROMPT = """Eres Lex, un asistente legal profesional de AboLegal. 
Responde como un abogado experto pero accesible. Sé empático pero profesional.

Directrices:
- Analiza el problema legal del usuario
- Proporciona orientación legal inicial
- Sugiere posibles acciones
- Sé claro y conciso (máximo 250 palabras)
- Mantén el tono en español

Ejemplo de respuesta adecuada:
"Entiendo tu situación. Los despidos sin indemnización pueden ser injustificados. Te recomiendo reunir toda la documentación: contrato, finiquito, etc. Podrías tener derecho a reclamo por despido injustificado. ¿Tienes algún documento que acredite tu relación laboral?""""

@app.route("/widget", methods=["GET"])
def widget():
    """Endpoint específico para el widget"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AboLegal Widget</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                margin: 0; 
                padding: 0; 
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #f8f9fa;
                height: 100vh;
                overflow: hidden;
            }
            .chat-container {
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            .chat-header {
                background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
                color: white;
                padding: 15px 20px;
                text-align: center;
                font-weight: 600;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            #chat-window {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: white;
            }
            .message {
                margin-bottom: 15px;
                padding: 12px 16px;
                border-radius: 18px;
                line-height: 1.4;
                max-width: 85%;
                animation: fadeIn 0.3s ease-in;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .user {
                background: #1a237e;
                color: white;
                margin-left: auto;
                border-bottom-right-radius: 6px;
            }
            .assistant {
                background: #f1f3f4;
                color: #333;
                border: 1px solid #e0e0e0;
                margin-right: auto;
                border-bottom-left-radius: 6px;
            }
            .input-container {
                padding: 20px;
                background: white;
                border-top: 1px solid #e0e0e0;
            }
            .input-row {
                display: flex;
                gap: 10px;
            }
            #user-input {
                flex: 1;
                padding: 12px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 25px;
                outline: none;
                font-size: 14px;
            }
            #user-input:focus {
                border-color: #1a237e;
            }
            #send-button {
                padding: 12px 20px;
                background: #1a237e;
                color: white;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-weight: 600;
            }
            #send-button:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .typing {
                color: #666;
                font-style: italic;
                padding: 12px 16px;
            }
            .dot-flashing {
                display: inline-block;
                position: relative;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #1a237e;
                animation: dotFlashing 1s infinite linear alternate;
                margin-left: 8px;
            }
            @keyframes dotFlashing {
                0% { background-color: #1a237e; }
                50%, 100% { background-color: rgba(26, 35, 126, 0.2); }
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                ⚖️ Asesor Legal AboLegal
            </div>
            <div id="chat-window"></div>
            <div class="input-container">
                <div class="input-row">
                    <input type="text" id="user-input" placeholder="Escribe tu consulta legal..." autocomplete="off">
                    <button id="send-button">Enviar</button>
                </div>
            </div>
        </div>

        <script>
            const chatWindow = document.getElementById('chat-window');
            const userInput = document.getElementById('user-input');
            const sendButton = document.getElementById('send-button');
            
            let messageHistory = [];

            function appendMessage(sender, message) {
                const msgDiv = document.createElement('div');
                msgDiv.className = `message ${sender}`;
                msgDiv.innerHTML = message.replace(/\n/g, '<br>');
                chatWindow.appendChild(msgDiv);
                chatWindow.scrollTop = chatWindow.scrollHeight;
            }

            // Mensaje inicial
            document.addEventListener('DOMContentLoaded', () => {
                appendMessage('assistant', '¡Hola! Soy Lex, tu asistente legal de AboLegal. ¿En qué puedo ayudarte con tu situación legal hoy?');
            });

            async function sendMessage() {
                const message = userInput.value.trim();
                if (!message) return;

                appendMessage('user', message);
                userInput.value = '';
                sendButton.disabled = true;
                userInput.disabled = true;

                // Indicador de typing
                const typingIndicator = document.createElement('div');
                typingIndicator.className = 'typing';
                typingIndicator.innerHTML = 'Lex está analizando tu caso<span class="dot-flashing"></span>';
                chatWindow.appendChild(typingIndicator);
                chatWindow.scrollTop = chatWindow.scrollHeight;

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ 
                            message: message,
                            session_id: 'widget_' + Date.now()
                        })
                    });

                    const data = await response.json();
                    
                    // Remover typing
                    chatWindow.removeChild(typingIndicator);
                    
                    if (data.reply) {
                        appendMessage('assistant', data.reply);
                    } else {
                        throw new Error('Respuesta vacía del servidor');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    chatWindow.removeChild(typingIndicator);
                    appendMessage('assistant', '🔧 No pudimos procesar tu consulta. Por favor, intenta nuevamente en unos momentos.');
                } finally {
                    sendButton.disabled = false;
                    userInput.disabled = false;
                    userInput.focus();
                }
            }

            // Event listeners
            sendButton.addEventListener('click', sendMessage);
            userInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });

            userInput.focus();
        </script>
    </body>
    </html>
    """)

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return '', 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        user_msg = data.get("message", "").strip()
        if not user_msg:
            return jsonify({"reply": "Por favor, escribe tu consulta legal."})

        logger.info(f"Received message: {user_msg}")

        # Llamar a Gemini con formato correcto
        try:
            response = model.generate_content(
                f"{LEGAL_PROMPT}\n\nConsulta del usuario: {user_msg}"
            )
            reply = response.text.strip()
            logger.info("Successfully got response from Gemini")
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            reply = "🔍 Estoy analizando tu caso de despido. Por el momento, te recomiendo: Reunir toda tu documentación laboral (contrato, liquidaciones, etc.) y contactar directamente con nuestro equipo al +56 X XXX XXXX para una asesoría personalizada."

        return jsonify({"reply": reply})

    except Exception as e:
        logger.error(f"General error: {str(e)}")
        return jsonify({"reply": "⚖️ Como abogado especializado, te recomiendo documentar todo por escrito y buscar asesoría legal presencial. Puedes contactarnos en info@abolegal.cl"}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "AboLegal Chatbot"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
