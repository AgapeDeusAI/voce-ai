from flask import Flask, request, jsonify
from flask_cors import CORS
from VoiceAI import VoiceAI  # Deve contenere la logica di sintesi vocale
import logging
import os

# --- Configurazione Logging ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
logger = logging.getLogger("VoiceAPI")

# --- Inizializzazione App Flask ---
app = Flask(__name__)
CORS(app)

# --- Inizializzazione del modulo vocale ---
try:
    voce_ai = VoiceAI()
    logger.info("✅ VoiceAI inizializzato correttamente.")
except Exception as e:
    logger.critical(f"❌ Errore critico inizializzando VoiceAI: {e}")
    raise SystemExit("Impossibile avviare il server vocale. Controllare VoiceAI.py.")

# --- Endpoints API ---
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "✅ Voce AI attiva",
        "descrizione": "Modulo per la sintesi vocale Agape",
        "versione_api": "1.0"
    }), 200

@app.route("/voce/sintetizza", methods=["POST"])
def sintetizza_voce():
    """
    Richiede la sintesi vocale. Parametri accettati:
    - testo (str): Il testo da pronunciare (obbligatorio)
    - voce (str): 'maschile' o 'femminile' (opzionale)
    - velocita (int): Velocità parlato (opzionale, default 170)
    """
    logger.info("➡️ Richiesta POST /voce/sintetizza ricevuta.")
    data = request.get_json(silent=True)

    if not data or "testo" not in data:
        logger.warning("⚠️ Richiesta JSON non valida o parametro 'testo' mancante.")
        return jsonify({
            "success": False,
            "message": "Parametro obbligatorio 'testo' mancante o JSON non valido."
        }), 400

    testo = data["testo"]
    voce = data.get("voce", "femminile")
    velocita = data.get("velocita", 170)

    # Validazioni aggiuntive
    if not isinstance(testo, str) or not testo.strip():
        return jsonify({
            "success": False,
            "message": "Il testo deve essere una stringa non vuota."
        }), 400

    try:
        velocita = int(velocita)
        if velocita <= 0:
            raise ValueError
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Il parametro 'velocita' deve essere un numero intero positivo."
        }), 400

    # Sintesi
    try:
        risultato = voce_ai.sintetizza_voce(testo=testo, voce=voce, velocita=velocita)
        if risultato.get("success"):
            logger.info("✅ Sintesi vocale completata.")
            return jsonify(risultato), 200
        else:
            logger.error(f"❌ Sintesi fallita: {risultato.get('message')}")
            return jsonify(risultato), 500
    except Exception as e:
        logger.exception("❌ Errore imprevisto durante la sintesi vocale.")
        return jsonify({
            "success": False,
            "message": f"Errore interno del server: {str(e)}"
        }), 500

# --- Avvio Server ---
if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 3003))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    logger.info(f"Server in esecuzione su http://{host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)