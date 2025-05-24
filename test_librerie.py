try:
    import pyttsx3
    import speech_recognition
    import librosa
    import soundfile
    import requests
    print("✅ Tutte le librerie sono installate correttamente.")
except Exception as e:
    print(f"❌ Errore: {e}")