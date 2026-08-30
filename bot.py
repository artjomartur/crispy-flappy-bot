import cv2
import numpy as np
import mss
import pyautogui
import time
import keyboard

# WARNUNG: PyAutoGUI benötigt Accessibility (Bedienungshilfen) Rechte auf dem Mac!

def start_bot():
    print("Bot startet in 3 Sekunden. Wechsle jetzt zum Spiel-Fenster!")
    time.sleep(3)
    print("Bot läuft! Drücke 'q', um den Bot zu beenden.")
    
    # Hier definierst du den Bereich deines Bildschirms, auf dem das Spiel läuft.
    # Du musst diese Werte eventuell anpassen.
    # top, left, width, height
    monitor = {"top": 200, "left": 200, "width": 600, "height": 800}
    
    # Template für den Vogel und/oder die Röhren laden (Du musst vorher Screenshots davon machen!)
    # bird_img = cv2.imread('bird_template.png', 0)
    # pipe_img = cv2.imread('pipe_template.png', 0)
    
    with mss.mss() as sct:
        while not keyboard.is_pressed('q'):
            # 1. Screenshot machen
            screenshot = np.array(sct.grab(monitor))
            
            # Konvertiere Bild zu Graustufen (besser für Erkennung)
            gray_frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
            
            # -------------------------------------------------------------
            # PLATZHALTER: BILDERKENNUNG
            # Hier würde die Logik stehen, um den Vogel und die Röhren zu finden.
            # z.B. per cv2.matchTemplate(gray_frame, bird_img, cv2.TM_CCOEFF_NORMED)
            # 
            # Da das Spiel auf Farben basiert, kann man auch nach spezifischen 
            # Farbwerten der Röhren scannen und die Distanz berechnen.
            # -------------------------------------------------------------
            
            # BEISPIEL-LOGIK (Simuliert einen Sprung)
            # Wenn eine Bedingung erfüllt ist (z.B. Vogel fällt zu tief oder Röhre kommt näher)
            jump_needed = False 
            
            if jump_needed:
                pyautogui.press('space')
                # Kurze Pause um Spamming zu verhindern
                time.sleep(0.1)
                
            # (Optional) Zeige an, was der Bot sieht (kann das System verlangsamen)
            # cv2.imshow('Bot Vision', gray_frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #    break

    cv2.destroyAllWindows()
    print("Bot beendet.")

if __name__ == "__main__":
    start_bot()
