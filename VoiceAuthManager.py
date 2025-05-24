from VoiceRecognizer import VoiceRecognizer
import logging
import datetime

# Logging Agape-friendly
logger = logging.getLogger("VoiceAuthManager")
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

class VoiceAuthManager:
    """
    Gestisce la registrazione e il riconoscimento vocale per identificare l'Admin.
    Pensato per integrazione modulare nel sistema Agape.
    """

    def __init__(self, threshold=0.6, admin_file="admin_voice.pkl", nome_admin="Admin"):
        self.recognizer = VoiceRecognizer(similarity_threshold=threshold, admin_file=admin_file)
        self.nome_admin = nome_admin
        self.threshold = threshold
        logger.info(f"VoiceAuthManager pronto per '{nome_admin}' con soglia {threshold}")

    def registra_admin(self, duration=5, callback=None):
        logger.info(f"Avvio registrazione voce di '{self.nome_admin}' ({duration}s)")
        successo = self.recognizer.registra_e_salva_admin(duration=duration)

        esito = {
            "success": successo,
            "message": "Voce Admin registrata con successo." if successo else "Errore nella registrazione vocale.",
            "timestamp": str(datetime.datetime.now())
        }

        if successo:
            logger.info(f"✅ {esito['message']}")
        else:
            logger.error(f"❌ {esito['message']}")

        if callback:
            callback("voce_admin_registrata", esito)

        return esito

    def verifica_admin(self, duration=5, callback=None):
        logger.info(f"Verifica in corso... ({duration}s)")

        successo, messaggio = self.recognizer.confronta_voce_con_admin(duration=duration)

        esito = {
            "success": successo,
            "message": "Accesso consentito." if successo else "Accesso negato.",
            "dettagli": messaggio,
            "timestamp": str(datetime.datetime.now())
        }

        if successo:
            logger.info(f"✅ {esito['message']} - {messaggio}")
        else:
            logger.warning(f"❌ {esito['message']} - {messaggio}")

        if callback:
            callback("verifica_voce_admin", esito)

        return esito