import unittest
from VoiceAI import VoiceAI
import time

class TestVoiceAI(unittest.TestCase):
    def setUp(self):
        self.ai = VoiceAI(voce="femminile", lingua="it", velocita=160)

    def test_voce_femminile(self):
        result = self.ai.sintetizza_voce("Test voce femminile")
        self.assertTrue(result["success"])

    def test_voce_maschile(self):
        result = self.ai.sintetizza_voce("Test voce maschile", voce="maschile")
        self.assertTrue(result["success"])

    def test_velocita_bassa(self):
        result = self.ai.sintetizza_voce("Velocità bassa", velocita=100)
        self.assertTrue(result["success"])

    def test_velocita_alta(self):
        result = self.ai.sintetizza_voce("Velocità alta", velocita=250)
        self.assertTrue(result["success"])

    def test_testo_vuoto(self):
        result = self.ai.sintetizza_voce("")
        self.assertFalse(result["success"])

    def test_stop_sintesi(self):
        self.ai.sintetizza_voce("Test interruzione")
        time.sleep(1)
        result = self.ai.stop_sintesi()
        self.assertIn("success", result)

    def tearDown(self):
        self.ai.cleanup()

if __name__ == "__main__":
    unittest.main()
