from GoogleSpeaker import GoogleSpeaker # Assicurati che GoogleSpeaker sia accessibile
import logging
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
from pathlib import Path
import sys # Importato per la configurazione del logger

class VoiceAI:
    """
    Interfaccia di alto livello per la sintesi vocale utilizzando Google Cloud Text-to-Speech.
    Gestisce l'inizializzazione del motore vocale, la sintesi del testo, il salvataggio
    dei file audio/testo e la riproduzione.
    """

    def __init__(self, voce: str = 'femminile', lingua: str = 'it', velocita: int = 100,
                 output_dir: str = "storage/audio"):
        """
        Inizializza l'istanza di VoiceAI.

        Args:
            voce (str): Il genere della voce predefinito ('femminile' o 'maschile').
            lingua (str): Il codice della lingua predefinito ('it' o 'en').
            velocita (int): La velocità di riproduzione predefinita in percentuale (es. 100 per normale).
            output_dir (str): La directory base dove salvare i file audio e testo.
        """
        self.logger = logging.getLogger("VoiceAI")
        self.output_directory = Path(output_dir)

        try:
            # Inizializza GoogleSpeaker con i parametri di default
            self.vocal_engine = GoogleSpeaker(voce=voce, lingua=lingua)
            self.vocal_engine.set_velocita(velocita)
            
            # Crea la directory di output se non esiste
            self.output_directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✅ VoiceAI (Google) initialized. Output directory: '{self.output_directory}'")
        except Exception as e:
            self.logger.critical(f"❌ Critical error during GoogleSpeaker initialization: {e}", exc_info=True)
            # Rilancia l'eccezione perché l'oggetto non può funzionare senza il motore vocale
            raise

    def sintetizza_voce(self, testo: str, voce: Optional[str] = None, 
                        velocita: Optional[int] = None, play_audio: bool = True) -> Dict[str, Any]:
        """
        Sintetizza un dato testo in voce, salva l'audio e il testo, e opzionalmente riproduce l'audio.

        Args:
            testo (str): Il testo da sintetizzare.
            voce (Optional[str]): Genere della voce da usare per questa sintesi ('femminile' o 'maschile').
                                  Se None, usa il default dell'istanza.
            velocita (Optional[int]): Velocità di riproduzione in percentuale per questa sintesi.
                                     Se None, usa il default dell'istanza.
            play_audio (bool): Se True, riproduce l'audio dopo la sintesi.

        Returns:
            Dict[str, Any]: Un dizionario contenente lo stato dell'operazione, un messaggio,
                            e il percorso del file audio in caso di successo.
        """
        if not testo or not testo.strip():
            self.logger.warning("⚠️ Attempted to synthesize an empty or whitespace-only text.")
            return {"success": False, "message": "Empty or invalid text provided."}

        # Salva lo stato corrente del motore vocale per ripristinarlo
        original_voce = self.vocal_engine.voce
        original_lingua = self.vocal_engine.lingua # Potrebbe essere utile anche la lingua
        original_velocita = self.vocal_engine.velocita

        # Imposta i parametri specifici per questa sintesi, se forniti
        # Nota: La lingua è impostata dalla voce, quindi set_voce gestisce entrambe
        if voce:
            # Qui si potrebbe passare anche la lingua se fosse un parametro di sintetizza_voce
            # Per ora, la lingua resta quella di default dell'istanza
            self.vocal_engine.set_voce(voce, self.vocal_engine.lingua)
        if velocita:
            self.vocal_engine.set_velocita(velocita)

        # Genera nomi di file univoci basati su timestamp e UUID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:6]
        filename_base = f"agape_{timestamp}_{unique_id}"

        mp3_path = self.output_directory / f"{filename_base}.mp3"
        txt_path = self.output_directory / f"{filename_base}.txt"

        try:
            # Salva il testo originale nel file TXT
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(testo)
            self.logger.info(f"Testo originale salvato in: {txt_path}")
        except IOError as e: # Cattura errori specifici di I/O
            self.logger.error(f"❌ Error saving text file '{txt_path}': {e}", exc_info=True)
            # Ripristina lo stato originale in caso di errore prima del TTS
            self.vocal_engine.set_voce(original_voce, original_lingua) # Assumendo che set_voce gestisca anche la lingua
            self.vocal_engine.set_velocita(int(original_velocita * 100)) # Converto float in int per set_velocita
            return {"success": False, "message": f"Error saving text file: {e}"}
        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred while saving text file: {e}", exc_info=True)
            self.vocal_engine.set_voce(original_voce, original_lingua)
            self.vocal_engine.set_velocita(int(original_velocita * 100))
            return {"success": False, "message": f"Unexpected error: {e}"}


        # Esegue la sintesi vocale tramite GoogleSpeaker
        success = self.vocal_engine.parla(testo, output_file=str(mp3_path), play_audio=play_audio)

        # Ripristina i parametri originali del motore vocale
        self.vocal_engine.set_voce(original_voce, original_lingua)
        self.vocal_engine.set_velocita(int(original_velocita * 100))

        if success:
            self.logger.info(f"✅ Synthesis completed. Audio: {mp3_path}, Text: {txt_path}")
            return {"success": True, "message": "Speech synthesis completed.", "audio_file": str(mp3_path)}
        else:
            self.logger.error(f"❌ Speech synthesis failed for text: '{testo[:50]}...'")
            return {"success": False, "message": "Speech synthesis failed."}

    def stop_sintesi(self) -> Dict[str, Any]:
        """
        Tenta di fermare una sintesi vocale in corso.
        Nota: L'API di Google TTS è sincrona e non supporta l'interruzione di una sintesi già avviata.
        Questo metodo serve principalmente per compatibilità con eventuali futuri motori vocali.

        Returns:
            Dict[str, Any]: Un dizionario indicante lo stato dell'operazione.
        """
        self.logger.info("ℹ️ Stop operation called. Google TTS is synchronous and does not support stopping in-progress synthesis.")
        return {"success": False, "message": "Stop not supported for Google TTS (synchronous API)."}

    def cleanup(self) -> None:
        """
        Esegue operazioni di pulizia per l'istanza di VoiceAI.
        Attualmente, non ci sono risorse persistenti da liberare per GoogleSpeaker.
        """
        self.logger.info("🧹 VoiceAI cleanup completed. No persistent engine resources to clear for GoogleSpeaker.")


# --- Esempio di Utilizzo ---
if __name__ == '__main__':
    # Configura il logger per l'intera applicazione
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        stream=sys.stdout)

    # Assicurati che la variabile d'ambiente GOOGLE_APPLICATION_CREDENTIALS sia impostata.
    # Esempio (NON farlo in produzione, usa gcloud auth application-default login):
    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/your/google_service_account_key.json"

    print("\n--- Inizializzazione VoiceAI ---")
    try:
        # Inizializza VoiceAI con parametri di default
        ai_speaker = VoiceAI(voce='femminile', lingua='it', velocita=100)
    except Exception as e:
        print(f"Impossibile inizializzare VoiceAI. Verificare la configurazione di Google Cloud: {e}")
        sys.exit(1) # Esce se l'inizializzazione fallisce

    print("\n--- Test 1: Sintesi base in italiano (default) ---")
    result1 = ai_speaker.sintetizza_voce("C'è un sole splendente a Concordia Sagittaria oggi, 24 maggio 2025.")
    if result1["success"]:
        print(f"Test 1 riuscito. File audio: {result1['audio_file']}")
    else:
        print(f"Test 1 fallito: {result1['message']}")

    print("\n--- Test 2: Sintesi con voce maschile e velocità modificata ---")
    result2 = ai_speaker.sintetizza_voce(
        "Hello, this is a test of a male voice speaking a bit faster.",
        voce='maschile',
        velocita=130 # 130% della velocità normale
    )
    if result2["success"]:
        print(f"Test 2 riuscito. File audio: {result2['audio_file']}")
    else:
        print(f"Test 2 fallito: {result2['message']}")

    print("\n--- Test 3: Sintesi di testo vuoto (dovrebbe fallire con un avviso) ---")
    result3 = ai_speaker.sintetizza_voce("   ")
    if not result3["success"]:
        print(f"Test 3 gestito correttamente: {result3['message']}")
    else:
        print(f"Test 3 fallito (il testo vuoto è stato sintetizzato per errore).")

    print("\n--- Test 4: Sintesi con parametri non validi (verrà usato il fallback interno a GoogleSpeaker) ---")
    # VoiceAI passerà 'invalid_voice' e 'very_fast' a GoogleSpeaker, che applicherà i suoi fallback
    result4 = ai_speaker.sintetizza_voce(
        "Questa frase dovrebbe essere sintetizzata con i parametri di fallback del motore vocale.",
        voce='voce_non_esistente',
        velocita=500 # Valore molto alto, verrà clampato
    )
    if result4["success"]:
        print(f"Test 4 riuscito. File audio: {result4['audio_file']}")
    else:
        print(f"Test 4 fallito: {result4['message']}")

    print("\n--- Chiamata al metodo stop_sintesi (per dimostrazione) ---")
    stop_result = ai_speaker.stop_sintesi()
    print(f"Risultato stop: {stop_result['message']}")

    print("\n--- Cleanup finale ---")
    ai_speaker.cleanup()
