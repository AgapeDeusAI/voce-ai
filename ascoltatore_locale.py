
import speech_recognition as sr
import requests
import time
import logging
import threading
import os
import sys
from langdetect import detect

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KEYWORD = os.getenv("VOICE_ASSISTANT_KEYWORD", "agape").lower()
TRIGGER_LISTEN_TIMEOUT = float(os.getenv("VOICE_ASSISTANT_TRIGGER_TIMEOUT", 5))
PHRASE_RECORD_DURATION = float(os.getenv("VOICE_ASSISTANT_PHRASE_DURATION", 4))
SYNTHESIS_ENDPOINT = os.getenv("VOICE_ASSISTANT_SYNTHESIS_ENDPOINT", "http://localhost:3003/voce/sintetizza")

recognizer = sr.Recognizer()
microfono = sr.Microphone()

def detect_language(text):
    try:
        lang = detect(text)
        logger.info(f"🌍 Lingua rilevata: {lang}")
        return lang
    except Exception as e:
        logger.warning(f"❌ Errore rilevamento lingua: {e}")
        return "it"  # fallback

def synthesize_text_async(text_to_synthesize: str, lingua_rilevata: str = "it"):
    def _send_request():
        try:
            logger.info(f"📤 Invio frase a sintesi vocale: '{text_to_synthesize[:50]}...' (Lingua: {lingua_rilevata})")
            response = requests.post(SYNTHESIS_ENDPOINT, json={"testo": text_to_synthesize, "lingua": lingua_rilevata})
            response.raise_for_status()
            json_response = response.json()
            if json_response.get("success"):
                logger.info("✅ Sintesi vocale completata.")
            else:
                logger.error(f"❌ Fallimento sintesi: {json_response.get('message', 'Nessun messaggio')}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Errore HTTP: {e}")
        except ValueError:
            logger.error("❌ Risposta JSON non valida.")
        except Exception as e:
            logger.exception(f"❌ Errore inaspettato durante la sintesi: {e}")
    threading.Thread(target=_send_request, daemon=True).start()

def listen_for_trigger(timeout_seconds: float = TRIGGER_LISTEN_TIMEOUT) -> bool:
    with microfono as source:
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.info(f"🎧 In ascolto per la parola chiave '{KEYWORD}' ({timeout_seconds}s)...")
            audio = recognizer.listen(source, timeout=timeout_seconds)
        except sr.WaitTimeoutError:
            logger.debug("⏳ Nessun parlato rilevato.")
            return False
        except Exception as e:
            logger.error(f"❌ Errore ascolto trigger: {e}")
            return False
    try:
        text = recognizer.recognize_google(audio, language="it-IT").lower()
        logger.info(f"🗣️ Riconosciuto: '{text}'")
        return KEYWORD in text
    except sr.UnknownValueError:
        logger.debug("❌ Audio non compreso.")
        return False
    except sr.RequestError as e:
        logger.error(f"❌ Errore Google Speech Recognition: {e}")
        return False
    except Exception as e:
        logger.exception(f"❌ Errore trigger: {e}")
        return False

def record_and_recognize_phrase(duration_seconds: float = PHRASE_RECORD_DURATION):
    with microfono as source:
        try:
            logger.info(f"🎙️ Parla ora ({duration_seconds}s)...")
            audio = recognizer.record(source, duration=duration_seconds)
        except Exception as e:
            logger.error(f"❌ Errore durante la registrazione: {e}")
            return None
    try:
        phrase = recognizer.recognize_google(audio, language="it-IT")
        logger.info(f"✅ Frase riconosciuta: '{phrase}'")
        return phrase
    except sr.UnknownValueError:
        logger.warning("❌ Frase non compresa.")
    except sr.RequestError as e:
        logger.error(f"❌ Errore Google Speech Recognition: {e}")
    except Exception as e:
        logger.exception(f"❌ Errore riconoscimento frase: {e}")
    return None

def main_loop():
    logger.info("🚀 Voice Assistant avviato. Ctrl+C per uscire.")
    try:
        while True:
            if listen_for_trigger():
                phrase = record_and_recognize_phrase()
                if phrase:
                    lang = detect_language(phrase)
                    synthesize_text_async(phrase, lang)
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("👋 Assistente vocale interrotto manualmente.")
    except Exception as e:
        logger.critical(f"Errore fatale nel ciclo principale: {e}", exc_info=True)
    finally:
        logger.info("Voice Assistant terminato.")

if __name__ == "__main__":
    main_loop()
