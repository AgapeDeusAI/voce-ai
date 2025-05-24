import logging
from VoceAgape import VoceAgape
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "agape-voice-key.json"

logging.basicConfig(level=logging.INFO)

agape = VoceAgape(voce="femminile", lingua="it", velocita=100)
agape.parla("Ciao, sono Agape. La tua voce intelligente.")