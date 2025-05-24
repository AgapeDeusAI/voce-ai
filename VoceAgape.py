import threading
import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from GoogleSpeaker import GoogleSpeaker # Assicurati che GoogleSpeaker sia nel tuo PYTHONPATH
from typing import Any
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
    # Il logger catturerà questo, non c'è bisogno di un sys.exit qui.

class VoceAgape:
    """
    Gestisce la sintesi vocale per Agape, dando priorità a Google Cloud TTS.
    Se Google Cloud TTS non è disponibile o fallisce nell'inizializzazione,
    effettua il fallback a pyttsx3 per la sintesi vocale locale.

    Attributes:
        use_google (bool): Indica se Google Cloud TTS è in uso.
        google_engine (Optional[GoogleSpeaker]): Istanza di GoogleSpeaker se in uso.
        pyttsx3_engine (Optional[pyttsx3.Engine]): Istanza di pyttsx3.Engine se in uso.
    """

    _LOGGER = logging.getLogger(__name__)

    # Mappatura delle lingue e generi supportati per pyttsx3 (esempi, potrebbe richiedere personalizzazione)
    _PYTTSX3_VOICE_PREFS = {
        'it': {
            'femminile': ['ita', 'italian', 'female'], # Parole chiave per identificare la voce italiana femminile
            'maschile': ['ita', 'italian', 'male']
        },
        'en': {
            'femminile': ['eng', 'english', 'female'],
            'maschile': ['eng', 'english', 'male']
        }
    }

    def __init__(self, voce: str = "femminile", lingua: str = "it", velocita: int = 100):
        """
        Inizializza il motore vocale. Tenta prima Google TTS, poi pyttsx3.

        Args:
            voce (str): Il genere della voce predefinito ('femminile' o 'maschile').
            lingua (str): Il codice della lingua predefinito ('it' o 'en').
            velocita (int): La velocità di riproduzione predefinita in percentuale (es. 100).
        """
        self.voce_predefinita = voce
        self.lingua_predefinita = lingua
        self.velocita_predefinita = velocita

        self.use_google: bool = False
        self.google_engine: Optional[GoogleSpeaker] = None
        self.pyttsx3_engine: Optional[Any] = None
        self._pyttsx3_voice_thread: Optional[threading.Thread] = None # Per gestire il thread di pyttsx3

        self._initialize_engines()

        # Imposta i parametri iniziali sul motore attivo
        self.set_velocita(velocita)
        self.set_voce(voce, lingua) # Chiama il setter per applicare la logica di selezione voce

        if not self.use_google and self.pyttsx3_engine is None:
            self._LOGGER.critical("❌ Nessun motore vocale disponibile (Google TTS fallito e pyttsx3 non inizializzato/installato).")
            # È utile sollevare un'eccezione qui se l'applicazione non può funzionare senza un motore vocale
            raise RuntimeError("Nessun motore vocale disponibile.")

    def _initialize_engines(self):
        """Tenta di inizializzare GoogleSpeaker, poi pyttsx3 come fallback."""
        try:
            self.google_engine = GoogleSpeaker(
                voce=self.voce_predefinita,
                lingua=self.lingua_predefinita
            )
            self.use_google = True
            self._LOGGER.info("✅ VoceAgape inizializzata con Google Cloud TTS.")
        except Exception as e:
            self._LOGGER.warning(f"⚠️ Impossibile inizializzare Google Cloud TTS. Dettagli: {e}. Tentativo di fallback con pyttsx3.")
            self.use_google = False
            self.google_engine = None # Assicurati che sia None

        if not self.use_google:
            if pyttsx3:
                try:
                    self.pyttsx3_engine = pyttsx3.init()
                    # Pre-cache delle voci di pyttsx3 per una selezione più veloce
                    self._cached_pyttsx3_voices = self._get_pyttsx3_voice_info()
                    self._LOGGER.info("✅ VoceAgape inizializzata con pyttsx3 (fallback).")
                except Exception as e:
                    self._LOGGER.critical(f"❌ Impossibile inizializzare pyttsx3: {e}", exc_info=True)
                    self.pyttsx3_engine = None
            else:
                self._LOGGER.critical("❌ pyttsx3 non è installato. Nessun fallback vocale disponibile.")

    def _get_pyttsx3_voice_info(self) -> List[Dict[str, Any]]:
        """
        Raccoglie informazioni dettagliate sulle voci disponibili di pyttsx3.
        """
        voices_info = []
        if not self.pyttsx3_engine:
            return voices_info
        try:
            for voice in self.pyttsx3_engine.getProperty("voices"):
                voices_info.append({
                    "id": voice.id,
                    "name": voice.name.lower(), # Converti in minuscolo per la ricerca
                    "languages": [lang.lower() for lang in voice.languages], # Converti in minuscolo
                    "gender": "female" if "female" in voice.name.lower() or "femenina" in voice.name.lower() else "male"
                })
            self._LOGGER.debug(f"Voci pyttsx3 disponibili: {voices_info}")
        except Exception as e:
            self._LOGGER.error(f"Errore nel recupero delle voci pyttsx3: {e}", exc_info=True)
        return voices_info

    def set_voce(self, voce: str, lingua: str) -> bool:
        """
        Imposta la voce (genere) e la lingua per il motore vocale attivo.

        Args:
            voce (str): Genere della voce ('femminile' o 'maschile').
            lingua (str): Codice della lingua ('it' o 'en').

        Returns:
            bool: True se la voce è stata impostata con successo, False altrimenti.
        """
        self.voce_predefinita = voce # Aggiorna le preferenze dell'istanza
        self.lingua_predefinita = lingua

        if self.use_google and self.google_engine:
            return self.google_engine.set_voce(voce, lingua)
        elif self.pyttsx3_engine:
            self._LOGGER.info(f"Tentativo di impostare la voce pyttsx3: '{voce}' per lingua '{lingua}'")
            return self._set_pyttsx3_voice(voce, lingua)
        else:
            self._LOGGER.warning("Nessun motore vocale attivo per impostare la voce.")
            return False

    def _set_pyttsx3_voice(self, voce: str, lingua: str) -> bool:
        """Logica interna per la selezione della voce pyttsx3."""
        if not self.pyttsx3_engine:
            return False

        voce_lower = voce.lower()
        lingua_lower = lingua.lower()

        # Priorità 1: Cerca una corrispondenza esatta basata su lingua e genere
        for v_info in self._cached_pyttsx3_voices:
            if any(l_code == lingua_lower for l_code in v_info["languages"]) and v_info["gender"] == voce_lower:
                self.pyttsx3_engine.setProperty("voice", v_info["id"])
                self._LOGGER.info(f"Voce pyttsx3 impostata: '{v_info['name']}' (ID: {v_info['id']})")
                return True

        # Priorità 2: Cerca una corrispondenza parziale nel nome se non trovata esatta
        self._LOGGER.warning(f"Voce pyttsx3 esatta non trovata per '{voce_lower}' ({lingua_lower}). Tentativo di corrispondenza parziale.")
        keywords = self._PYTTSX3_VOICE_PREFS.get(lingua_lower, {}).get(voce_lower, [])

        for v_info in self._cached_pyttsx3_voices:
            if all(k in v_info["name"] for k in keywords):
                self.pyttsx3_engine.setProperty("voice", v_info["id"])
                self._LOGGER.info(f"Voce pyttsx3 impostata (corrispondenza parziale): '{v_info['name']}' (ID: {v_info['id']})")
                return True
        
        self._LOGGER.warning(f"Nessuna voce pyttsx3 trovata per '{voce_lower}' in '{lingua_lower}'. Usando la voce di default.")
        return False # Nessuna voce specifica trovata, userà il default di pyttsx3 o l'ultima impostata

    def set_velocita(self, velocita: int) -> bool:
        """
        Imposta la velocità di riproduzione per il motore vocale attivo.

        Args:
            velocita (int): La velocità desiderata in percentuale (es. 100 per normale).

        Returns:
            bool: True se la velocità è stata impostata, False altrimenti.
        """
        self.velocita_predefinita = velocita # Aggiorna la preferenza dell'istanza

        if self.use_google and self.google_engine:
            return self.google_engine.set_velocita(velocita)
        elif self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.setProperty("rate", velocita)
                self._LOGGER.info(f"Velocità pyttsx3 impostata a: {velocita}")
                return True
            except Exception as e:
                self._LOGGER.error(f"Errore nell'impostazione della velocità pyttsx3: {e}", exc_info=True)
                return False
        else:
            self._LOGGER.warning("Nessun motore vocale attivo per impostare la velocità.")
            return False

    def parla(self, testo: str, play_audio: bool = True) -> bool:
        """
        Sintetizza e riproduce il testo. Se Google TTS è in uso, lo fa in modo sincrono.
        Se pyttsx3 è in uso, lo fa in un thread separato per evitare di bloccare l'UI.

        Args:
            testo (str): Il testo da pronunciare.
            play_audio (bool): Se True, riproduce l'audio dopo la sintesi.

        Returns:
            bool: True se la sintesi è stata avviata con successo, False altrimenti.
        """
        if not testo or not testo.strip():
            self._LOGGER.warning("Tentativo di pronunciare un testo vuoto o composto solo da spazi bianchi.")
            return False

        if self.use_google and self.google_engine:
            self._LOGGER.info("Utilizzo Google Cloud TTS per la pronuncia.")
            # GoogleSpeaker gestisce già il salvataggio e la riproduzione in modo sincrono
            return self.google_engine.parla(testo, play_audio=play_audio)
        
        elif self.pyttsx3_engine:
            if self._pyttsx3_voice_thread and self._pyttsx3_voice_thread.is_alive():
                self._LOGGER.warning("⚠️ La voce pyttsx3 è già in esecuzione. Ignoro la nuova richiesta.")
                return False

            self._LOGGER.info("Utilizzo pyttsx3 per la pronuncia (in thread separato).")
            # Pyttsx3.runAndWait() blocca, quindi lo eseguiamo in un thread separato
            def _speak_pyttsx3():
                try:
                    self.pyttsx3_engine.say(testo)
                    self.pyttsx3_engine.runAndWait()
                    self._LOGGER.info("Pronuncia pyttsx3 completata.")
                except Exception as e:
                    self._LOGGER.error(f"Errore durante la pronuncia con pyttsx3: {e}", exc_info=True)
            
            self._pyttsx3_voice_thread = threading.Thread(target=_speak_pyttsx3, daemon=True)
            self._pyttsx3_voice_thread.start()
            return True
        else:
            self._LOGGER.error("❌ Nessun motore vocale attivo per la sintesi.")
            return False

    def stop_parla(self) -> bool:
        """
        Tenta di fermare la riproduzione vocale in corso.
        Funziona solo con pyttsx3. Google TTS è asincrono e non può essere interrotto.

        Returns:
            bool: True se la riproduzione è stata interrotta, False se non supportato o fallito.
        """
        if self.use_google:
            self._LOGGER.info("Stop non supportato per Google Cloud TTS (sincrono).")
            return False
        
        if self.pyttsx3_engine:
            try:
                if self._pyttsx3_voice_thread and self._pyttsx3_voice_thread.is_alive():
                    self.pyttsx3_engine.stop() # Interrompe la riproduzione
                    self._pyttsx3_voice_thread.join(timeout=1) # Attendi che il thread termini
                    if self._pyttsx3_voice_thread.is_alive():
                        self._LOGGER.warning("Il thread di pyttsx3 non è terminato dopo l'interruzione.")
                    self._LOGGER.info("Riproduzione pyttsx3 interrotta.")
                    return True
                else:
                    self._LOGGER.info("Nessuna riproduzione pyttsx3 attiva da fermare.")
                    return False
            except Exception as e:
                self._LOGGER.error(f"Errore durante l'interruzione della riproduzione pyttsx3: {e}", exc_info=True)
                return False
        else:
            self._LOGGER.warning("Nessun motore pyttsx3 attivo per interruzioni.")
            return False

    def cleanup(self):
        """
        Esegue la pulizia delle risorse del motore vocale.
        Per pyttsx3, è importante chiamare questo metodo per liberare risorse.
        """
        self._LOGGER.info("🧹 Avvio pulizia risorse VoceAgape.")
        if self.pyttsx3_engine:
            try:
                # Assicurati che non ci siano thread di runAndWait bloccati
                self.pyttsx3_engine.stop()
                if self._pyttsx3_voice_thread and self._pyttsx3_voice_thread.is_alive():
                    self._pyttsx3_voice_thread.join(timeout=1) # Dai tempo al thread di terminare
                self._LOGGER.info("Risorse pyttsx3 liberate.")
            except Exception as e:
                self._LOGGER.error(f"Errore durante la pulizia di pyttsx3: {e}", exc_info=True)
        # GoogleSpeaker non ha una cleanup esplicita per il suo client HTTP
        self._LOGGER.info("✅ Pulizia VoceAgape completata.")


# --- Esempio di Utilizzo ---
if __name__ == '__main__':
    import sys
    # Configura il logging per l'intera applicazione
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        stream=sys.stdout)

    print("\n--- Inizializzazione VoceAgape ---")
    speaker = None
    try:
        # Tenta di inizializzare VoceAgape, che userà Google o pyttsx3
        speaker = VoceAgape(voce='femminile', lingua='it', velocita=170)
    except RuntimeError as e:
        print(f"Errore fatale: {e}. Impossibile avviare VoceAgape. Assicurati che GOOGLE_APPLICATION_CREDENTIALS sia impostato o che pyttsx3 sia installato.")
        sys.exit(1)
    except Exception as e:
        print(f"Errore generico durante l'inizializzazione: {e}")
        sys.exit(1)

    # Verifica quale motore è stato usato
    if speaker.use_google:
        print("\n=== Utilizzo Google Cloud TTS ===")
    elif speaker.pyttsx3_engine:
        print("\n=== Utilizzo pyttsx3 (Fallback) ===")
    else:
        print("\n=== Nessun motore vocale attivo ===")
        sys.exit(1)

    print("\n--- Test 1: Sintesi di una frase ---")
    speaker.parla("Ciao, sono Agape, la tua assistente vocale. Questo è un test del mio sistema vocale.")
    time.sleep(4) # Dai tempo alla voce di finire, soprattutto per pyttsx3 in thread

    print("\n--- Test 2: Cambiare voce e lingua (se supportato dal motore attivo) ---")
    if speaker.set_voce('maschile', 'en'):
        print("Voce cambiata con successo.")
        speaker.parla("Hello, this is Agape's male voice, speaking in English.")
        time.sleep(3)
    else:
        print("Impossibile cambiare voce/lingua.")

    print("\n--- Test 3: Provare a parlare mentre un'altra voce è in esecuzione (solo per pyttsx3) ---")
    if speaker.pyttsx3_engine: # Se stiamo usando pyttsx3
        speaker.parla("Questo è un test di interruzione. Dovrebbe riprodursi per primo.")
        time.sleep(1) # Inizia a riprodurre
        print("Tentativo di parlare mentre la voce è già in esecuzione...")
        speaker.parla("Questa frase non dovrebbe essere pronunciata se la precedente è ancora in corso.")
        time.sleep(2) # Dai tempo al logger di mostrare l'avviso
        speaker.stop_parla()
        print("Riproduzione interrotta.")
        time.sleep(1) # Un breve ritardo per sicurezza
        speaker.parla("La riproduzione è stata interrotta e ora ricomincio.")
        time.sleep(3)
    else:
        print("Test 3 non applicabile a Google TTS.")

    print("\n--- Test 4: Cambiare velocità ---")
    speaker.set_velocita(80)
    speaker.parla("Ora parlo un po' più lentamente per voi. Spero sia chiaro.")
    time.sleep(3)
    speaker.set_velocita(180)
    speaker.parla("E ora parlo decisamente più in fretta, riuscite a seguirmi?")
    time.sleep(3)

    print("\n--- Test 5: Testo vuoto ---")
    speaker.parla("   ") # Dovrebbe loggare un warning e non fare nulla

    print("\n--- Pulizia finale ---")
    speaker.cleanup()
    print("Programma terminato.")
