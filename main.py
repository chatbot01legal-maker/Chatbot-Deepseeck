from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import google.generativeai as genai
import uuid
from datetime import datetime

app = Flask(__name__)
# CORS para desarrollo y producción
CORS(app, origins=["https://www.abolegal.cl", "http://localhost:3000", "https://*.onrender.com"])

# API key de Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Por favor define GEMINI_API_KEY en las variables de entorno de Render.")

genai.configure(api_key=API_KEY)
model_name = "gemini-2.0-flash"  # Cambiado a versión estable
model = genai.GenerativeModel(model_name)

# Almacenamiento simple en memoria (para desarrollo)
chat_sessions = {}

INITIAL_PROMPT = """Eres Lex, un asistente legal profesional de AboLegal. 
Tu rol es:
1. Escuchar activamente los problemas legales del usuario
2. Hacer preguntas claras para entender el caso
3. Proporcionar orientación legal inicial
4. Mantener un tono profesional pero empático

Responde siempre en español y sé conciso (máximo 300 palabras)."""

# --- HTML del chat ---
CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AboLegal Chatbot</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            max-width: 600px; 
            margin: 0 auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .chat-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .chat-header {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .chat-header h1 {
            margin: 0;
            font-size: 1.5em;
        }
        .chat-header .subtitle {
            opacity: 0.8;
            font-size: 0.9em;
        }
        #chat-window { 
            height: 400px; 
            overflow-y: auto; 
            padding: 20px;
            background: #f8f9fa;
        }
        .message { 
            margin-bottom: 15px; 
            padding: 12px 16px;
            border-radius: 18px;
            line-height: 1.4;
            max-width: 80%;
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .user { 
            background: #007bff;
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }
        .assistant { 
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            margin-right: auto;
            border-bottom-left-radius: 4px;
        }
        .typing {
            color: #666;
            font-style: italic;
        }
        #input-container { 
            display: flex; 
            padding: 20px;
            background: white;
            border-top: 1px solid #eee;
        }
        #user-input { 
            flex-grow: 1; 
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
        }
        #user-input:focus {
            border-color: #007bff;
        }
        #send-button { 
            padding: 12px 24px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            margin-left: 10px;
            font-weight: 600;
            transition: background 0.2s;
        }
        #send-button:hover:not(:disabled) {
            background: #0056b3;
        }
        #send-button:disabled { 
            background: #ccc;
            cursor: not-allowed;
        }
        .message-time {
            font-size: 0.75em;
            opacity: 0.6;
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>⚖️ AboLegal Assistant</h1>
            <div class="subtitle">Asistente Legal Inteligente</div>
        </div>
        <div id="chat-window"></div>
        <div id="input-container">
            <input type="text" id="user-input" placeholder="Describe tu situación legal..." autocomplete="off">
            <button id="send-button">Enviar</button>
        </div>
    </div>

    <script>
        const chatWindow = document.getElementById('chat-window');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        
        // Generar session ID único
        const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
        let messageHistory = [];

        function appendMessage(sender, message) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', sender);
            
            const time = new Date().toLocaleTimeString('es-ES', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            
            msgDiv.innerHTML = `
                <div>${message.replace(/\n/g, '<br>')}</div>
                <div class="message-time">${time}</div>
            `;
            
            chatWindow.appendChild(msgDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        // Mensaje inicial
        document.addEventListener('DOMContentLoaded', () => {
            appendMessage('assistant', 'Hola, soy Lex, tu asesor legal de AboLegal. ¿En qué puedo ayudarte hoy? Cuéntame brevemente tu situación legal.');
        });

        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;

            appendMessage('user', message);
            messageHistory.push({ role: 'user', content: message });
            userInput.value = '';
            sendButton.disabled = true;
            userInput.disabled = true;

            // Indicador de typing
            const typingIndicator = document.createElement('div');
            typingIndicator.id = 'typing-indicator';
            typingIndicator.classList.add('message', 'assistant', 'typing');
            typingIndicator.innerHTML = 'Lex está analizando tu caso...';
            chatWindow.appendChild(typingIndicator);
            chatWindow.scrollTop = chatWindow.scrollHeight;

            try {
                // URL dinámica del backend
                const backend_url = window.location.origin + '/chat';
                
                const response = await fetch(backend_url, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        message: message,
                        session_id: sessionId,
                        history: messageHistory
                    })
                });

                if (!response.ok) {
                    throw new Error(`Error ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                
                // Remover indicador de typing
                if (document.getElementById('typing-indicator')) {
                    chatWindow.removeChild(typingIndicator);
                }
                
                appendMessage('assistant', data.reply);
                messageHistory.push({ role: 'assistant', content: data.reply });
                
            } catch (error) {
                console.error('Error:', error);
                if(document.getElementById('typing-indicator')) {
                    chatWindow.removeChild(typingIndicator);
                }
                appendMessage('assistant', '⚠️ Lo siento, hubo un error de conexión. Por favor, intenta nuevamente.');
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
    </script>
</body>
</html>
"""

# --- Rutas de Flask ---
@app.route("/", methods=["GET"])
def index():
    return render_template_string(CHAT_HTML)

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return '', 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        user_msg = data.get("message", "").strip()
        session_id = data.get("session_id", "default")
        history = data.get("history", [])

        if not user_msg:
            return jsonify({"reply": "Por favor, escribe tu consulta legal."})

        # Construir contexto de conversación
        conversation = [{"role": "user", "parts": [INITIAL_PROMPT]}]
        
        # Agregar historial reciente (últimos 6 mensajes para contexto)
        recent_history = history[-6:] if len(history) > 6 else history
        for msg in recent_history:
            conversation.append({"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]})

        # Agregar mensaje actual
        conversation.append({"role": "user", "parts": [user_msg]})

        try:
            # Llamar a Gemini
            response = model.generate_content(conversation)
            reply = response.text.strip()
        except Exception as e:
            reply = f"🔧 Estamos mejorando el servicio. Por favor, reformula tu pregunta o intenta nuevamente en unos momentos. Error: {str(e)}"

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": "❌ Error interno del servidor. Por favor, recarga la página e intenta nuevamente."}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "AboLegal Chatbot"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
