import os
import logging
from google.cloud import texttospeech
import sys
from typing import Optional
# Tenta di importare playsound per la riproduzione audio.
# Se non disponibile, lo gestiamo graziosamente.
try:
    from playsound import playsound
except ImportError:
    playsound = None

class GoogleSpeaker:
    """
    Sintetizza testo in voce usando Google Cloud Text-to-Speech.

    Richiede che la variabile d'ambiente GOOGLE_APPLICATION_CREDENTIALS
    sia impostata sul percorso di un file JSON valido della chiave di servizio
    di Google Cloud, oppure che l'applicazione sia autenticata in altro modo
    (es. gcloud auth application-default login).

    Attributes:
        logger (logging.Logger): Logger per la classe.
        client (texttospeech.TextToSpeechClient): Client API di Google TTS.
        _voce (str): Genere della voce ('femminile' o 'maschile').
        _lingua (str): Codice della lingua (es. 'it', 'en').
        _velocita (float): Velocità di riproduzione (0.25 a 4.0).
        _custom_voice_name (Optional[str]): Nome specifico della voce di Google da usare.
    """

    # Voci e lingue supportate con mapping diretto ai codici Google BCP-47
    # e nomi specifici per le voci Neural2, che offrono qualità superiore.
    _SUPPORTED_VOICES = {
        'it': {
            'femminile': {'code': 'it-IT', 'name': 'it-IT-Wavenet-C'},
            'maschile': {'code': 'it-IT', 'name': 'it-IT-Wavenet-B'}
        },
        'en': {
            'femminile': {'code': 'en-US', 'name': 'en-US-Neural2-J'},
            'maschile': {'code': 'en-US', 'name': 'en-US-Neural2-I'}
        },
        'fr': {
            'femminile': {'code': 'fr-FR', 'name': 'fr-FR-Neural2-B'},
            'maschile': {'code': 'fr-FR', 'name': 'fr-FR-Neural2-D'}
        },
        'es': {
            'femminile': {'code': 'es-ES', 'name': 'es-ES-Neural2-A'},
            'maschile': {'code': 'es-ES', 'name': 'es-ES-Neural2-C'}
        },
        # Lingue con fallback a en-US se non esistono voci neurali specifiche o richieste
        'ig': {'femminile': {'code': 'en-US', 'name': 'en-US-Neural2-J'},
               'maschile': {'code': 'en-US', 'name': 'en-US-Neural2-I'}}
    }

    _MIN_SPEED = 0.25 # Velocità minima API di Google
    _MAX_SPEED = 4.0  # Velocità massima API di Google

    def __init__(self, voce: str = 'femminile', lingua: str = 'it'):
        self.logger = logging.getLogger(__name__)
        
        try:
            self.client = texttospeech.TextToSpeechClient()
            self.logger.info("Client Google Cloud Text-to-Speech inizializzato.")
        except Exception as e:
            self.logger.critical(f"Errore nell'inizializzazione del client Google TTS. "
                                 f"Controlla GOOGLE_APPLICATION_CREDENTIALS o la connessione: {e}")
            raise # Rilancia l'eccezione, l'istanza non può funzionare senza client

        # Imposta i valori iniziali tramite i setter per la convalida
        self._voce = 'femminile'
        self._lingua = 'it'
        self._velocita = 0.85
        self._custom_voice_name: Optional[str] = None # Inizializza l'attributo

        self.set_voce(voce, lingua) # Chiama set_voce per impostare voce, lingua e custom_voice_name
        self.set_velocita(100) # Inizializza a velocità normale (100% = 1.0)

        if playsound is None:
            self.logger.warning(
                "La libreria 'playsound' non è installata. "
                "La riproduzione audio diretta tramite Python potrebbe non funzionare. "
                "Verrà tentato 'mpg123' come fallback."
            )

    @property
    def voce(self) -> str:
        return self._voce

    @property
    def lingua(self) -> str:
        return self._lingua

    @property
    def velocita(self) -> float:
        return self._velocita

    def set_voce(self, voce: str, lingua: str) -> bool:
        """
        Imposta la voce (femminile/maschile) e la lingua per la sintesi.
        Vengono applicati valori di fallback e avvisi per input non validi.
        Tenta di selezionare una voce Neural2 specifica se disponibile.

        Args:
            voce (str): Il genere della voce desiderato ('femminile' o 'maschile').
            lingua (str): Il codice della lingua desiderata (es. 'it', 'en', 'fr', 'es', 'ig').

        Returns:
            bool: True se i parametri sono stati impostati (anche con fallback), False altrimenti.
        """
        voce_set = False
        lingua_set = False
        self._custom_voice_name = None # Resetta ogni volta che si imposta la voce

        # Cerca la lingua nel dizionario supportato
        lang_data = self._SUPPORTED_VOICES.get(lingua)
        if lang_data:
            self._lingua = lingua
            lingua_set = True
            
            # Cerca il genere della voce per la lingua selezionata
            voice_data = lang_data.get(voce)
            if voice_data:
                self._voce = voce
                self._custom_voice_name = voice_data.get('name')
                voce_set = True
            else:
                self.logger.warning(f"Voce '{voce}' non supportata per la lingua '{lingua}'. Impostata a 'femminile'.")
                self._voce = 'femminile' # Fallback genere
                # Tenta di usare la voce femminile predefinita per la lingua data
                if 'femminile' in lang_data:
                    self._custom_voice_name = lang_data['femminile'].get('name')
        else:
            self.logger.warning(f"Lingua '{lingua}' non supportata. Impostata a 'it' come fallback.")
            self._lingua = 'it' # Fallback lingua
            # Applica il fallback anche per la voce in questo caso, usando i default italiani
            if voce in self._SUPPORTED_VOICES['it']:
                self._voce = voce
                self._custom_voice_name = self._SUPPORTED_VOICES['it'][voce].get('name')
            else:
                self.logger.warning(f"Voce '{voce}' non supportata per la lingua di fallback 'it'. Impostata a 'femminile'.")
                self._voce = 'femminile'
                self._custom_voice_name = self._SUPPORTED_VOICES['it']['femminile'].get('name')

        if not lingua_set or not voce_set:
            self.logger.info(f"Parametri voce aggiornati con fallback: lingua='{self.lingua}', voce='{self.voce}', nome_voce='{self._custom_voice_name}'.")
        else:
            self.logger.info(f"Parametri voce aggiornati: lingua='{self.lingua}', voce='{self.voce}', nome_voce='{self._custom_voice_name}'.")
        return True

    def set_velocita(self, velocita_percentuale: int) -> bool:
        """
        Imposta la velocità di riproduzione della voce.

        Args:
            velocita_percentuale (int): La velocità desiderata in percentuale (es. 100 per normale).
                                       Internamente sarà mappata tra 0.25 e 4.0.

        Returns:
            bool: True se la velocità è stata impostata, False altrimenti.
        """
        if not isinstance(velocita_percentuale, (int, float)):
            self.logger.error(f"Input non valido per la velocità: {velocita_percentuale}. Deve essere un numero.")
            return False

        # Clampa l'input percentuale in un range ragionevole per evitare comportamenti estremi
        clamped_percent = max(0, min(velocita_percentuale, 400)) # Clampa tra 0% e 400%

        # Converte la percentuale in un fattore per l'API (es. 100 -> 1.0)
        new_speed = clamped_percent / 100.0

        # Assicura che la velocità rientri nei limiti dell'API (0.25 - 4.0)
        self._velocita = max(self._MIN_SPEED, min(new_speed, self._MAX_SPEED))
        
        self.logger.info(f"Velocità impostata a {self._velocita:.2f} (da input percentuale {velocita_percentuale}%).")
        return True

    def parla(self, testo: str, output_file: str = "output_google.mp3", play_audio: bool = True) -> bool:
        """
        Sintetizza il testo in voce utilizzando Google Cloud Text-to-Speech.
        Salva l'audio in un file MP3 e, opzionalmente, lo riproduce.

        Args:
            testo (str): Il testo da sintetizzare.
            output_file (str): Il percorso del file dove salvare l'audio MP3.
            play_audio (bool): Se True, tenterà di riprodurre l'audio dopo la sintesi.

        Returns:
            bool: True se la sintesi e il salvataggio sono riusciti, False altrimenti.
        """
        if not testo or not testo.strip():
            self.logger.warning("Tentativo di sintetizzare un testo vuoto. Nessuna operazione.")
            return False

        try:
            # Recupera il codice lingua e il nome della voce personalizzata
            current_lang_data = self._SUPPORTED_VOICES.get(self._lingua)
            if not current_lang_data:
                self.logger.error(f"Configurazione lingua non valida per '{self._lingua}'.")
                return False
            
            # Seleziona la voce in base al nome personalizzato o al genere
            if self._custom_voice_name:
                voice_params = texttospeech.VoiceSelectionParams(
                    language_code=current_lang_data[self._voce]['code'],
                    name=self._custom_voice_name
                )
                self.logger.info(f"Voce selezionata (custom): {self._custom_voice_name}")
            else:
                # Fallback al genere se non c'è un nome specifico (anche se _custom_voice_name dovrebbe esserci sempre qui)
                gender_enum = texttospeech.SsmlVoiceGender.FEMALE if self._voce == 'femminile' else texttospeech.SsmlVoiceGender.MALE
                voice_params = texttospeech.VoiceSelectionParams(
                    language_code=current_lang_data[self._voce]['code'],
                    ssml_gender=gender_enum
                )
                self.logger.info(f"Voce selezionata (genere): {self._voce}")

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=self._velocita
            )

            synthesis_input = texttospeech.SynthesisInput(text=testo)
            
            self.logger.info(f"Inizio sintesi vocale: Lingua='{self._lingua}', Voce='{self._voce}', Velocità='{self._velocita:.2f}'")
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config
            )

            # Salva il contenuto audio
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
            self.logger.info(f"✅ Audio salvato con successo in '{output_file}'")

            # Riproduci l'audio se richiesto
            if play_audio:
                self._play_audio(output_file)
            return True

        except Exception as e:
            self.logger.error(f"❌ Errore critico durante la sintesi vocale con Google TTS: {e}", exc_info=True)
            return False

    def _play_audio(self, file_path: str):
        """
        Metodo interno per la riproduzione audio, gestisce playsound e fallback mpg123.
        """
        if not os.path.exists(file_path):
            self.logger.error(f"File audio non trovato per la riproduzione: {file_path}")
            return

        if playsound:
            try:
                self.logger.info(f"Riproduzione audio con 'playsound': {file_path}")
                playsound(file_path)
            except Exception as e:
                self.logger.error(f"Errore durante la riproduzione con 'playsound': {e}")
                self.logger.info(f"Tentativo di riproduzione con 'mpg123' come fallback...")
                self._play_audio_with_mpg123(file_path)
        else:
            self.logger.info(f"Riproduzione audio con 'mpg123' (playsound non disponibile): {file_path}")
            self._play_audio_with_mpg123(file_path)

    def _play_audio_with_mpg123(self, file_path: str):
        """
        Metodo interno per riprodurre audio usando il comando di sistema mpg123.
        """
        try:
            if sys.platform.startswith('linux') or sys.platform == 'darwin': # Linux o macOS
                command = f"mpg123 {file_path}"
                result = os.system(command)
                if result != 0:
                    self.logger.warning(
                        f"Il comando '{command}' è terminato con codice {result}. "
                        "Assicurati che 'mpg123' sia installato e nel PATH."
                    )
            elif sys.platform == 'win32': # Windows
                self.logger.warning(
                    f"Riproduzione audio diretta tramite comando di sistema non supportata "
                    f"nativamente per Windows con mpg123. Considera l'uso di 'playsound'."
                )
            else:
                self.logger.warning(f"Piattaforma '{sys.platform}' non supportata per la riproduzione audio diretta.")
        except Exception as e:
            self.logger.error(f"Errore durante l'esecuzione del comando mpg123: {e}")

# --- Esempio di utilizzo (quando lo script viene eseguito direttamente) ---
if __name__ == '__main__':
    # Configura il logging per l'intera applicazione
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        stream=sys.stdout) # Output del log sulla console

    # Assicurati di aver impostato GOOGLE_APPLICATION_CREDENTIALS
    # Ad esempio: os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/your/key.json"
    # Per il testing, puoi anche usare il login di gcloud: gcloud auth application-default login

    print("\n--- Inizializzazione GoogleSpeaker ---")
    try:
        # Test con una lingua supportata e voce specifica
        speaker_it_fem = GoogleSpeaker(voce='femminile', lingua='it')
        print("\n--- Test 1: Saluto in italiano femminile (Neural2-C) ---")
        speaker_it_fem.set_velocita(100)
        if speaker_it_fem.parla("Ciao, sono la voce femminile italiana di Neural2-C. Sono le 21:00 del 24 maggio 2025. Oggi a Concordia Sagittaria, il tempo è mite."):
            print("Test 1 completato con successo.")
        else:
            print("Test 1 fallito.")

        # Test con una lingua supportata e voce maschile
        speaker_en_masc = GoogleSpeaker(voce='maschile', lingua='en')
        print("\n--- Test 2: Saluto in inglese maschile (Neural2-I) ---")
        speaker_en_masc.set_velocita(90) # Un po' più lento
        if speaker_en_masc.parla("Hello, I am the English male voice Neural2-I. It's 9 PM on May 24th, 2025. In Concordia Sagittaria, the weather is mild."):
            print("Test 2 completato con successo.")
        else:
            print("Test 2 fallito.")
        
        # Test con una lingua non supportata (dovrebbe fallback a italiano)
        speaker_ig_fem = GoogleSpeaker(voce='femminile', lingua='ig') # Lingua 'ig' non supportata direttamente
        print("\n--- Test 3: Saluto con lingua 'ig' (dovrebbe fallback a italiano femminile) ---")
        speaker_ig_fem.set_velocita(100)
        if speaker_ig_fem.parla("Questo testo dovrebbe essere pronunciato in italiano perché la lingua 'ig' non è pienamente supportata."):
            print("Test 3 completato con successo (fallback lingua).")
        else:
            print("Test 3 fallito.")

        # Test con un genere non supportato per una lingua (dovrebbe fallback al genere supportato)
        # Assumendo che per es-ES 'neutra' non sia un genere valido, dovrebbe fallback a 'femminile'
        speaker_es_neutra = GoogleSpeaker(voce='neutra', lingua='es')
        print("\n--- Test 4: Saluto con genere 'neutra' per spagnolo (dovrebbe fallback a spagnolo femminile) ---")
        speaker_es_neutra.set_velocita(100)
        if speaker_es_neutra.parla("Este texto debería ser pronunciado en español femenino por defecto."):
            print("Test 4 completato con successo (fallback genere).")
        else:
            print("Test 4 fallito.")

        print("\n--- Test 5: Testo vuoto (dovrebbe produrre un avviso e non fare nulla) ---")
        if not speaker_it_fem.parla(""):
            print("Test 5 gestito correttamente (testo vuoto).")
        else:
            print("Test 5 fallito (testo vuoto non gestito correttamente).")

        print("\n--- Test 6: Velocità fuori range (dovrebbe essere clampata) ---")
        speaker_it_fem.set_velocita(500) # Oltre il 400%
        if speaker_it_fem.parla("Questa voce è incredibilmente veloce, ma entro i limiti dell'API!"):
            print("Test 6 completato con successo (velocità clampata).")
        else:
            print("Test 6 fallito.")

    except Exception as e:
        print(f"Errore critico durante l'inizializzazione o l'esecuzione dei test: {e}")
        sys.exit(1) # Esce se non può inizializzare il client o se i test falliscono in modo critico