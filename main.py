from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import google.generativeai as genai
import logging
import sys

# Configurar logging robusto
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-2024")

# Configuración CORS para producción
allowed_origins = [
    "https://www.abolegal.cl",
    "https://abolegal.cl", 
    "http://localhost:3000",
    "https://*.onrender.com"
]

CORS(app, origins=allowed_origins, supports_credentials=True)

# Validación crítica de API Key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logger.error("❌ GEMINI_API_KEY no está configurada en las variables de entorno")
    # No hacemos raise para evitar crash en render, pero logueamos el error
    API_KEY = "not-configured"

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("✅ Gemini AI configurado correctamente")
except Exception as e:
    logger.error(f"❌ Error configurando Gemini: {str(e)}")
    model = None

# Prompt legal mejorado
LEGAL_PROMPT = """Eres Lex, un asistente legal profesional de AboLegal. 
Responde como un abogado experto pero accesible. Sé empático pero profesional.

Directrices CRÍTICAS:
- Analiza el problema legal del usuario de manera estructurada
- Proporciona orientación legal inicial PRÁCTICA y ÚTIL
- Sé claro y conciso (máximo 200 palabras)
- Mantén el tono en español
- NO des asesoramiento legal definitivo
- Recomienda consultar con abogado para casos específicos

Ejemplo de respuesta adecuada:
"Entiendo tu situación con el despido. Los despidos sin indemnización pueden ser injustificados. Te recomiendo: 1) Reunir toda tu documentación laboral, 2) Solicitar por escrito el finiquito detallado, 3) Contactar a la Inspección del Trabajo. ¿Tienes tu contrato de trabajo a mano?""""

@app.route("/", methods=["GET"])
def index():
    """Página principal de diagnóstico"""
    return jsonify({
        "status": "active",
        "service": "AboLegal Legal Assistant API",
        "version": "2.0",
        "endpoints": {
            "chat": "/chat (POST)",
            "health": "/health (GET)", 
            "widget": "/widget (GET)"
        }
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de health check robusto"""
    gemini_status = "healthy" if model else "unavailable"
    
    return jsonify({
        "status": "healthy",
        "service": "AboLegal Chatbot",
        "gemini_status": gemini_status,
        "timestamp": os.getenv("RENDER_GIT_COMMIT", "local-dev")
    })

@app.route("/widget", methods=["GET"])
def widget():
    """Endpoint específico para el widget embebido"""
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>AboLegal - Asistente Legal</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .chat-container {
            width: 100%;
            max-width: 400px;
            height: 600px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .chat-header {
            background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
            color: white;
            padding: 20px;
            text-align: center;
            font-weight: 600;
            font-size: 18px;
        }
        #chat-window {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .message {
            padding: 12px 16px;
            border-radius: 18px;
            line-height: 1.4;
            max-width: 85%;
            word-wrap: break-word;
            animation: messageAppear 0.3s ease-out;
        }
        @keyframes messageAppear {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .user-message {
            background: #1a237e;
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 6px;
        }
        .assistant-message {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            margin-right: auto;
            border-bottom-left-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        .input-row {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        #user-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
            transition: border-color 0.3s ease;
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
            transition: background 0.3s ease;
        }
        #send-button:hover:not(:disabled) {
            background: #283593;
        }
        #send-button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .typing-indicator {
            padding: 12px 16px;
            color: #666;
            font-style: italic;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .typing-dots {
            display: flex;
            gap: 4px;
        }
        .typing-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #1a237e;
            animation: typingAnimation 1.4s infinite ease-in-out;
        }
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes typingAnimation {
            0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }
        .error-message {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ffcdd2;
            text-align: center;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            ⚖️ Asesor Legal AboLegal
        </div>
        <div id="chat-window">
            <div class="message assistant-message">
                ¡Hola! Soy Lex, tu asistente legal de AboLegal. Estoy aquí para orientarte en tu situación legal. ¿En qué puedo ayudarte hoy?
            </div>
        </div>
        <div class="input-container">
            <div class="input-row">
                <input type="text" id="user-input" placeholder="Describe tu situación legal..." autocomplete="off">
                <button id="send-button">Enviar</button>
            </div>
        </div>
    </div>

    <script>
        class LegalChat {
            constructor() {
                this.chatWindow = document.getElementById('chat-window');
                this.userInput = document.getElementById('user-input');
                this.sendButton = document.getElementById('send-button');
                this.messageHistory = [];
                
                this.init();
            }
            
            init() {
                this.sendButton.addEventListener('click', () => this.sendMessage());
                this.userInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') this.sendMessage();
                });
                this.userInput.focus();
            }
            
            addMessage(sender, content, isError = false) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}-message ${isError ? 'error-message' : ''}`;
                messageDiv.textContent = content;
                this.chatWindow.appendChild(messageDiv);
                this.chatWindow.scrollTop = this.chatWindow.scrollHeight;
            }
            
            showTyping() {
                const typingDiv = document.createElement('div');
                typingDiv.className = 'typing-indicator';
                typingDiv.id = 'typing-indicator';
                typingDiv.innerHTML = `
                    Lex está analizando tu caso
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                `;
                this.chatWindow.appendChild(typingDiv);
                this.chatWindow.scrollTop = this.chatWindow.scrollHeight;
            }
            
            hideTyping() {
                const typingIndicator = document.getElementById('typing-indicator');
                if (typingIndicator) {
                    typingIndicator.remove();
                }
            }
            
            async sendMessage() {
                const message = this.userInput.value.trim();
                if (!message) return;
                
                // Limpiar input y deshabilitar temporalmente
                this.userInput.value = '';
                this.sendButton.disabled = true;
                this.userInput.disabled = true;
                
                // Mostrar mensaje del usuario
                this.addMessage('user', message);
                
                // Mostrar indicador de typing
                this.showTyping();
                
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
                    
                    if (!response.ok) {
                        throw new Error(`Error ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    this.hideTyping();
                    
                    if (data.reply) {
                        this.addMessage('assistant', data.reply);
                    } else {
                        throw new Error('Respuesta vacía del servidor');
                    }
                    
                } catch (error) {
                    console.error('Error en el chat:', error);
                    this.hideTyping();
                    this.addMessage('assistant', '⚠️ No pudimos procesar tu consulta en este momento. Por favor, intenta nuevamente o contacta directamente con nuestro equipo.', true);
                } finally {
                    this.sendButton.disabled = false;
                    this.userInput.disabled = false;
                    this.userInput.focus();
                }
            }
        }
        
        // Inicializar el chat cuando el DOM esté listo
        document.addEventListener('DOMContentLoaded', () => {
            new LegalChat();
        });
    </script>
</body>
</html>
""")

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    """Endpoint principal del chat - Robustecido"""
    if request.method == "OPTIONS":
        return '', 200
        
    try:
        # Validar JSON
        if not request.is_json:
            return jsonify({"reply": "Error: Se esperaba JSON"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"reply": "Error: JSON vacío"}), 400
            
        user_msg = data.get("message", "").strip()
        if not user_msg:
            return jsonify({"reply": "Por favor, escribe tu consulta legal."}), 400
            
        logger.info(f"📩 Mensaje recibido: {user_msg[:100]}...")
        
        # Verificar configuración de Gemini
        if not model:
            logger.error("Gemini no configurado - usando respuesta de fallback")
            return jsonify({
                "reply": "🔧 Nuestro asistente está en mantenimiento. Por favor, contacta directamente con nuestro equipo legal al +56 X XXX XXXX o info@abolegal.cl para asistencia inmediata."
            })
        
        # Llamar a Gemini con manejo robusto de errores
        try:
            response = model.generate_content(
                f"{LEGAL_PROMPT}\n\nConsulta del usuario: {user_msg}\n\nRespuesta:"
            )
            reply = response.text.strip()
            logger.info("✅ Respuesta de Gemini generada exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error de Gemini API: {str(e)}")
            # Respuesta de fallback útil
            reply = f"""Entiendo que {user_msg.lower().split('.')[0]}. 

Por el momento, nuestro sistema de IA está experimentando dificultades técnicas. 

Te recomiendo:
• Documentar toda la información relevante
• Contactar directamente con nuestro equipo legal
• Llamarnos al +56 X XXX XXXX

Estaremos encantados de ayudarte personalmente."""

        return jsonify({"reply": reply})

    except Exception as e:
        logger.error(f"💥 Error general en /chat: {str(e)}")
        return jsonify({
            "reply": "⚠️ Estamos experimentando problemas técnicos. Por favor, contacta directamente con nuestro equipo legal para asistencia inmediata."
        }), 500

# Manejo de errores global
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado", "status": 404}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Error interno del servidor", "status": 500}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
