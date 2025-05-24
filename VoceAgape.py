import pyttsx3
import threading
import logging
import time # Importa time per time.sleep
from typing import Optional, List, Dict, Any

# Configura il logging per l'intera applicazione, se non già fatto altrove
# Assicurati che non ci siano configurazioni multiple di basicConfig, altrimenti i log potrebbero duplicarsi.
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

class VoceAgape:
    """
    Gestisce la sintesi vocale di Agape usando pyttsx3 in modo asincrono e robusto.
    Supporta selezione dinamica di voce e lingua, e una gestione sicura del motore.
    Le voci disponibili vengono cachate all'inizializzazione.
    """

    def __init__(self, voce: str = "femminile", lingua: str = "it", velocita: int = 170):
        self.logger = logging.getLogger(__name__)
        try:
            self.engine = pyttsx3.init()
            # Imposta un callback per la fine della pronuncia per una gestione più pulita del thread
            self.engine.connect('finished-utterance', self._on_utterance_finish)
        except Exception as e:
            self.logger.critical(f"❌ Errore critico durante l'inizializzazione di pyttsx3: {e}")
            raise RuntimeError("Impossibile inizializzare il motore di sintesi vocale.") from e

        self.thread_parla: Optional[threading.Thread] = None
        self.voce_attualmente_impostata: Optional[str] = None
        self._cached_voices: List[Dict[str, Any]] = self._get_available_voices()

        self.set_velocita(velocita)
        # Assicurati che set_voce venga chiamato dopo il caching delle voci
        self.set_voce(voce, lingua)
        self.logger.info("VoceAgape inizializzato.")

    def _get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Restituisce una lista di voci disponibili con i loro attributi,
        mappando il genere numerico a una stringa.
        """
        voices_info = []
        try:
            for voice in self.engine.getProperty("voices"):
                gender_str = "unknown"
                if voice.gender == 0: # pyttsx3.Gender.FEMALE
                    gender_str = "female"
                elif voice.gender == 1: # pyttsx3.Gender.MALE
                    gender_str = "male"

                voices_info.append({
                    "id": voice.id,
                    "name": voice.name,
                    "languages": voice.languages,
                    "gender": gender_str # Usa la stringa mappata
                })
        except Exception as e:
            self.logger.error(f"❌ Errore nel recupero delle voci disponibili: {e}")
        return voices_info

    def set_velocita(self, velocita: int) -> bool:
        """Imposta la velocità della voce."""
        if not isinstance(velocita, int) or velocita <= 0:
            self.logger.warning(f"⚠️ Velocità non valida: {velocita}. Deve essere un intero positivo.")
            return False
        try:
            self.engine.setProperty("rate", velocita)
            self.logger.info(f"⚡ Velocità voce impostata a: {velocita}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Errore nell'impostazione della velocità: {e}")
            return False

    def set_voce(self, voce_preferita: str, lingua_preferita: str) -> bool:
        """
        Imposta la voce in base alla lingua e genere desiderati.
        Tenta di trovare la corrispondenza migliore, altrimenti sceglie un fallback.
        """
        voce_preferita = voce_preferita.lower()
        lingua_preferita = lingua_preferita.lower()

        best_match_id: Optional[str] = None
        fallback_id: Optional[str] = None

        for voce in self._cached_voices:
            voce_id_lower = voce['id'].lower()
            voce_name_lower = voce['name'].lower()

            if lingua_preferita in voce_id_lower or lingua_preferita in voce_name_lower:
                if voce_preferita == "femminile" and ("female" in voce['gender'] or any(n in voce_name_lower for n in ["alice", "federica", "monica"])):
                    best_match_id = voce['id']
                    break
                elif voce_preferita == "maschile" and "male" in voce['gender']:
                    best_match_id = voce['id']
                    break
                if fallback_id is None:
                    fallback_id = voce['id']

        voice_to_set = best_match_id if best_match_id else fallback_id

        if voice_to_set:
            try:
                self.engine.setProperty("voice", voice_to_set)
                self.voce_attualmente_impostata = voice_to_set
                voce_nome_reale = next((v['name'] for v in self._cached_voices if v['id'] == voice_to_set), "sconosciuta")
                self.logger.info(f"✅ Voce impostata su: '{voce_nome_reale}' (ID: {voice_to_set}). Richiesta: {voce_preferita}/{lingua_preferita}")
                return True
            except Exception as e:
                self.logger.error(f"❌ Errore nell'impostazione della voce '{voice_to_set}': {e}")
                return False
        else:
            self.logger.warning(f"⚠️ Nessuna voce corrispondente trovata per '{voce_preferita}'/'{lingua_preferita}'. Usando voce predefinita del sistema.")
            self.voce_attualmente_impostata = self.engine.getProperty('voice')
            return False

    def _on_utterance_finish(self, name: str, completed: bool) -> None:
        if completed:
            self.logger.info(f"✅ Pronuncia completata per '{name}'.")
        else:
            self.logger.warning(f"⚠️ Pronuncia interrotta per '{name}'.")
        self.thread_parla = None

    def parla(self, testo: str, ritardo_post_pronuncia: float = 0.5) -> bool:
        if not self.engine:
            self.logger.error("❌ Motore di sintesi vocale non inizializzato. Impossibile parlare.")
            return False

        if self.thread_parla and self.thread_parla.is_alive():
            self.logger.warning("⚠️ Voce già attiva. Attendere la fine della pronuncia corrente.")
            return False

        try:
            self.thread_parla = threading.Thread(
                target=self._speak_in_thread,
                args=(testo, ritardo_post_pronuncia),
                daemon=True
            )
            self.thread_parla.start()
            self.logger.info(f"🗣️ Avvio pronuncia del testo: '{testo[:70]}...'")
            return True
        except Exception as e:
            self.logger.error(f"❌ Errore durante l'avvio del thread di pronuncia: {e}")
            return False

    def _speak_in_thread(self, testo: str, ritardo_post_pronuncia: float) -> None:
        try:
            self.engine.startLoop(False)
            self.engine.say(testo)
            self.engine.runAndWait()
            self.engine.endLoop()
            if ritardo_post_pronuncia > 0:
                time.sleep(ritardo_post_pronuncia)
        except Exception as e:
            self.logger.error(f"❌ Errore durante la pronuncia nel thread: {e}")
            self.thread_parla = None

    def stop_parla(self) -> bool:
        if self.thread_parla and self.thread_parla.is_alive():
            try:
                self.engine.stop()
                self.thread_parla.join(timeout=0.5)
                if self.thread_parla and self.thread_parla.is_alive():
                    self.logger.warning("⚠️ Il thread di pronuncia non si è fermato completamente dopo l'interruzione.")
                else:
                    self.logger.info("🛑 Pronuncia interrotta con successo.")
                return True
            except Exception as e:
                self.logger.error(f"❌ Errore durante l'interruzione della pronuncia: {e}")
                return False
        self.logger.info("🗣️ Nessuna pronuncia attiva da fermare.")
        return False

    def cleanup(self) -> None:
        if self.engine:
            try:
                if self.thread_parla and self.thread_parla.is_alive():
                    self.engine.stop()
                    self.thread_parla.join(timeout=1)
                try:
                    self.engine.endLoop()
                except RuntimeError:
                    pass
                self.engine = None
                self.logger.info("🗑️ Motore vocale chiuso e risorse liberate.")
            except Exception as e:
                self.logger.error(f"❌ Errore durante la pulizia del motore vocale: {e}")
