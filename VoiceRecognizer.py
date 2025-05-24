import speech_recognition as sr
import os
import pickle
import numpy as np
import librosa
import logging

# Configura il logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class VoiceRecognizer:
    """
    Riconoscimento vocale basato su MFCC, salva e confronta impronte vocali.
    """

    def __init__(self, admin_file="admin_voice.pkl", sample_rate=22050, similarity_threshold=0.6):
        self.recognizer = sr.Recognizer()
        self.admin_file = admin_file
        self.sample_rate = sample_rate
        self.similarity_threshold = similarity_threshold
        self.admin_impronta = None
        logging.info("VoiceRecognizer inizializzato.")

    def _get_audio_from_microphone(self, duration=5, temp_file="temp_audio.wav"):
        with sr.Microphone() as source:
            logging.info(f"🎙️ Parla ora per {duration} secondi...")
            try:
                audio = self.recognizer.record(source, duration=duration)
                with open(temp_file, "wb") as f:
                    f.write(audio.get_wav_data())
                logging.info("✅ Registrazione completata.")
                return temp_file
            except Exception as e:
                logging.error(f"❌ Errore nella registrazione: {e}")
                return None

    def estrai_impronta(self, file_path):
        try:
            y, sr_audio = librosa.load(file_path, sr=self.sample_rate)
            mfcc = librosa.feature.mfcc(y=y, sr=self.sample_rate, n_mfcc=13)
            return np.mean(mfcc.T, axis=0)
        except Exception as e:
            logging.error(f"❌ Errore estrazione MFCC: {e}")
            return None

    def registra_e_salva_admin(self, duration=5):
        temp_file = self._get_audio_from_microphone(duration, "admin_temp.wav")
        if not temp_file:
            return False

        impronta = self.estrai_impronta(temp_file)
        if impronta is None:
            os.remove(temp_file)
            return False

        try:
            with open(self.admin_file, "wb") as f:
                pickle.dump(impronta, f)
            self.admin_impronta = impronta
            logging.info("✅ Impronta vocale admin salvata.")
            return True
        except Exception as e:
            logging.error(f"❌ Errore salvataggio impronta: {e}")
            return False
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def confronta_voce_con_admin(self, duration=5):
        if not os.path.exists(self.admin_file):
            return False, "⚠️ Impronta admin non trovata."

        if self.admin_impronta is None:
            try:
                with open(self.admin_file, "rb") as f:
                    self.admin_impronta = pickle.load(f)
            except Exception as e:
                return False, f"Errore caricamento admin: {e}"

        temp_file = self._get_audio_from_microphone(duration, "user_temp.wav")
        if not temp_file:
            return False, "Nessuna voce utente registrata."

        nuova_impronta = self.estrai_impronta(temp_file)
        if nuova_impronta is None:
            os.remove(temp_file)
            return False, "Errore estrazione impronta utente."

        distanza = np.linalg.norm(self.admin_impronta - nuova_impronta)
        simile = distanza < self.similarity_threshold
        logging.info(f"📊 Distanza: {distanza:.4f} | Soglia: {self.similarity_threshold}")
        if simile:
            logging.info("✅ Voce riconosciuta come Admin.")
        else:
            logging.info("❌ Voce diversa da Admin.")
        os.remove(temp_file)
        return simile, f"Distanza calcolata: {distanza:.4f}"

# Uso diretto per test
if __name__ == "__main__":
    vr = VoiceRecognizer()
    print("\n--- REGISTRAZIONE ADMIN ---")
    if vr.registra_e_salva_admin():
        print("\n--- CONFRONTO ---")
        admin, msg = vr.confronta_voce_con_admin()
        print(f"Risultato: {'Amministratore' if admin else 'Non riconosciuto'} – {msg}")
    else:
        print("Registrazione Admin fallita.")