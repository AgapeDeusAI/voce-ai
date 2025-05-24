from VoceAgape import VoceAgape
import logging
from typing import Optional, Dict, Any

class VoiceAI:
    """
    Manages speech synthesis operations, acting as a high-level interface
    for the underlying VoceAgape engine. It allows synthesizing text
    with dynamic options for voice and speed.
    """

    def __init__(self, voce: str = 'femminile', lingua: str = 'it', velocita: int = 170):
        self.logger = logging.getLogger("VoiceAI")
        self.vocal_engine: Optional[VoceAgape] = None
        try:
            # Initialize the VoceAgape engine with provided default settings
            self.vocal_engine = VoceAgape(voce=voce, lingua=lingua, velocita=velocita)
            self.logger.info("✅ VoiceAI successfully initialized.")
        except Exception as e:
            self.logger.critical(f"❌ Critical error during VoceAgape initialization: {e}. "
                                 "Ensure pyttsx3 is installed and a text-to-speech engine is available.")
            # Re-raise the exception to signal a fatal error to the calling application
            raise

    def sintetizza_voce(self, testo: str, voce: Optional[str] = None, velocita: Optional[int] = None) -> Dict[str, Any]:
        """
        Synthesizes the provided text into speech, with the option to dynamically override
        voice and speed settings for this specific synthesis.

        Args:
            testo (str): The text to synthesize.
            voce (Optional[str]): The type of voice to use for this synthesis ('femminile', 'maschile').
                                  If None, uses the default voice.
            velocita (Optional[int]): The speaking rate to use for this synthesis.
                                      If None, uses the default speed.

        Returns:
            Dict[str, Any]: A dictionary containing the operation status ('success': bool)
                            and a descriptive 'message'.
        """
        if not self.vocal_engine:
            self.logger.error("❌ Voice engine not initialized. Cannot synthesize speech.")
            return {"success": False, "message": "Voice synthesis engine not available."}

        if not testo or not testo.strip():
            self.logger.warning("⚠️ Attempted to synthesize an empty or whitespace-only text.")
            return {"success": False, "message": "Empty or invalid text provided."}

        # Dynamically set voice if provided for this request
        if voce is not None:
            # Use the engine's current language for the new voice setting
            if not self.vocal_engine.set_voce(voce, self.vocal_engine.lingua):
                self.logger.warning(f"⚠️ Failed to set voice to '{voce}' for this synthesis. Using current voice.")

        # Dynamically set speed if provided for this request
        if velocita is not None:
            if not self.vocal_engine.set_velocita(velocita):
                self.logger.warning(f"⚠️ Failed to set speed to '{velocita}' for this synthesis. Using current speed.")

        # Execute speech synthesis
        success = self.vocal_engine.parla(testo)

        if success:
            self.logger.info(f"✅ Speech synthesis successfully initiated for: '{testo[:70]}...'")
            return {"success": True, "message": "Speech synthesis started successfully."}
        else:
            # VoceAgape's parla() method logs more specific errors if it fails.
            self.logger.error(f"❌ Failed to initiate speech synthesis for: '{testo[:70]}...'. "
                              "The engine might be busy or encountered an internal error.")
            return {"success": False, "message": "Failed to start speech synthesis. The engine might be busy or not responding."}

    def stop_sintesi(self) -> Dict[str, Any]:
        """
        Stops any currently ongoing speech synthesis.

        Returns:
            Dict[str, Any]: A dictionary with the operation status.
        """
        if not self.vocal_engine:
            self.logger.error("❌ Voice engine not initialized. Cannot stop synthesis.")
            return {"success": False, "message": "Voice engine not available."}

        if self.vocal_engine.stop_parla():
            self.logger.info("🛑 Speech synthesis successfully stopped.")
            return {"success": True, "message": "Speech synthesis stopped."}
        else:
            self.logger.info("ℹ️ No active speech synthesis to stop.")
            return {"success": False, "message": "No active speech synthesis to stop."}

    def cleanup(self) -> None:
        """
        Cleans up the resources of the speech synthesis engine.
        This method should be called when the application is shutting down.
        """
        if self.vocal_engine:
            self.logger.info("🗑️ Initiating VoiceAI resource cleanup.")
            self.vocal_engine.cleanup()
            self.logger.info("✅ VoiceAI resource cleanup completed.")
