from VoiceAI import VoiceAI
import time

ai = VoiceAI(voce="femminile", lingua="it", velocita=170)

def menu():
    while True:
        print("\n--- Menu Voce AI ---")
        print("1. Parla")
        print("2. Cambia voce")
        print("3. Cambia velocità")
        print("4. Interrompi")
        print("5. Esci")
        scelta = input("Scelta: ")

        if scelta == "1":
            testo = input("Testo da pronunciare: ")
            ai.sintetizza_voce(testo)
            time.sleep(1)
        elif scelta == "2":
            voce = input("Voce (femminile/maschile): ").strip().lower()
            ai.vocal_engine.set_voce(voce, "it")
        elif scelta == "3":
            try:
                velocita = int(input("Nuova velocità: "))
                ai.vocal_engine.set_velocita(velocita)
            except ValueError:
                print("Inserisci un numero valido.")
        elif scelta == "4":
            ai.stop_sintesi()
        elif scelta == "5":
            ai.cleanup()
            print("Arrivederci!")
            break
        else:
            print("Scelta non valida.")

if __name__ == "__main__":
    menu()
