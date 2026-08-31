import cv2
import numpy as np
import mss
import time
import pyautogui
import subprocess

# WICHTIG: PyAutoGUI macht standardmäßig nach jedem Tastendruck eine Pause von 0.1 Sekunden!
# Das verursacht extremen Input-Lag in Spielen. Wir schalten das ab!
pyautogui.PAUSE = 0

# WARNUNG: PyAutoGUI benötigt Accessibility (Bedienungshilfen) Rechte auf dem Mac!

def get_active_window_bounds():
    script = '''
    tell application "System Events"
        set frontProcess to first application process whose frontmost is true
        set processName to name of frontProcess
        tell frontProcess
            set winList to every window
            repeat with win in winList
                try
                    set winPos to position of win
                    set winSize to size of win
                    if item 1 of winSize > 100 and item 2 of winSize > 100 then
                        return {processName, item 1 of winPos, item 2 of winPos, item 1 of winSize, item 2 of winSize}
                    end if
                end try
            end repeat
        end tell
    end tell
    return {"None", 0, 0, 0, 0}
    '''
    try:
        proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        res = proc.stdout.strip()
        if res:
            parts = [p.strip() for p in res.split(',')]
            if len(parts) >= 5:
                app_name = parts[0]
                left = int(parts[1])
                top = int(parts[2])
                width = int(parts[3])
                height = int(parts[4])
                return app_name, left, top, width, height
    except Exception as e:
        print("Fehler beim Erkennen des aktiven Fensters:", e)
    return None

def start_bot():
    print("Bot startet in 3 Sekunden. Wechsle jetzt zum Spiel-Fenster!")
    time.sleep(3)
    
    # Speichert die konstante X-Position des Vogels, um Hintergrundobjekte auszufiltern
    bird_initial_x = None
    bird_lost_frames = 0
    last_bird_x = None
    last_bird_y = None
    print("Bot läuft! Drücke 'q' im 'Bot Vision' Fenster, um den Bot zu beenden.")
    
    # Dynamisch das aktive Fenster nach dem 3-Sekunden-Countdown holen
    print("Erkenne aktives Spielfenster...")
    window_info = get_active_window_bounds()
    
    # Template für den Vogel laden
    bird_img = cv2.imread('bird_template.png', 0)
    
    if bird_img is None:
        print("Fehler: 'bird_template.png' nicht gefunden im Ordner!")
        return
    
    last_jump_time = 0
    
    with mss.mss() as sct:
        if window_info:
            app_name, left, top, width, height = window_info
            print(f"Spielfenster erkannt: App={app_name}, Position=({left}, {top}), Größe=({width}x{height})")
            print("WICHTIG: Verschiebe oder verändere die Größe des Fensters nach dem Start nicht mehr!")
            monitor = {"top": top, "left": left, "width": width, "height": height}
        else:
            print("Kein aktives Spielfenster erkannt. Verwende Standard-Bildschirm-Capture.")
            monitor = sct.monitors[1]
        
        while True:
            # Standard HUD-Variablen für diesen Frame initialisieren
            bird_y_val = "N/A"
            target_y_val = "N/A"
            reset_time_left = max(0.0, 3.0 - (time.time() - last_jump_time))
            status_text = "SUCHE VOGEL..."
            status_color = (0, 0, 255)  # Rot
            is_falling = False
            jump_needed = False
            target_y = 450  # Default fallback
            
            # 1. Screenshot machen
            screenshot = np.array(sct.grab(monitor))
            
            # Konvertiere Bild zu Graustufen (besser für Erkennung)
            gray_frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
            
            # --- 2. FARBERKENNUNG RÖHREN (Grün) ---
            # Konvertiere in den HSV-Farbraum für bessere Farberkennung
            hsv_frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR) # Erst BGR
            hsv_frame = cv2.cvtColor(hsv_frame, cv2.COLOR_BGR2HSV)   # Dann HSV
            
            # Flappy Bird Röhren sind hellgrün (Level 1) oder GOLD (Level 2).
            # Wir brauchen zwei Masken, um beide Farben zu erfassen.
            lower_green = np.array([30, 80, 80])
            upper_green = np.array([90, 255, 255])
            mask_green = cv2.inRange(hsv_frame, lower_green, upper_green)
            
            lower_gold = np.array([10, 80, 80])
            upper_gold = np.array([30, 255, 255])
            mask_gold = cv2.inRange(hsv_frame, lower_gold, upper_gold)
            
            mask_pipes = cv2.bitwise_or(mask_green, mask_gold)
            
            # Finde die Konturen der Röhren
            # WICHTIG: RETR_EXTERNAL ignoriert Löcher (wie den weißen Score-Zähler auf der Röhre)!
            contours, _ = cv2.findContours(mask_pipes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # --- 3. SPIEL-LOGIK (Lücke finden) ---
            jump_needed = False
            
            # --- 1. BILDERKENNUNG VOGEL (Farb-Erkennung) ---
            # Der Vogel dreht sich beim Fallen! Das Template-Matching schlägt dann fehl.
            # Da der Vogel das einzige rote Objekt ist, suchen wir einfach nach roten Pixeln.
            
            # HSV-Grenzen für Rot/Orange (etwas toleranter)
            lower_red1 = np.array([0, 100, 50])
            upper_red1 = np.array([20, 255, 255])
            lower_red2 = np.array([160, 100, 50])
            upper_red2 = np.array([180, 255, 255])
            
            mask_red1 = cv2.inRange(hsv_frame, lower_red1, upper_red1)
            mask_red2 = cv2.inRange(hsv_frame, lower_red2, upper_red2)
            mask_red = cv2.bitwise_or(mask_red1, mask_red2)
            
            bird_contours, _ = cv2.findContours(mask_red, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            bird_found = False
            valid_bird_contours = []
            for cnt in bird_contours:
                if cv2.contourArea(cnt) > 20:
                    bx, by, bw, bh = cv2.boundingRect(cnt)
                    # WICHTIG: Keine feste 'rechte Hälfte' Bedingung mehr! 
                    # Wir finden das echte Safari-Fenster überall, weil der echte Vogel 
                    # im Vollbild immer viel größer ist als sein 50%-Spiegelbild im Bot Vision Fenster.
                    if bw < 150 and bh < 150:
                        
                        # ANTI-LOGO CHECK: Das Spiel hat ein rotes Hühnchen-Logo AUF den grünen Röhren!
                        # Wir schauen uns einen Rahmen (+5 Pixel) um das rote Objekt an.
                        # Da das rote Logo selbst NICHT grün ist, schauen wir nur auf die absoluten grünen Pixel drumherum.
                        exp_x, exp_y = max(0, bx - 5), max(0, by - 5)
                        exp_w, exp_h = min(mask_pipes.shape[1] - exp_x, bw + 10), min(mask_pipes.shape[0] - exp_y, bh + 10)
                        roi_green = mask_pipes[exp_y:exp_y+exp_h, exp_x:exp_x+exp_w]
                        
                        if roi_green.size > 0:
                            green_pixels = cv2.countNonZero(roi_green)
                            border_area = roi_green.size - (bw * bh)
                            
                            if border_area > 0:
                                green_ratio = green_pixels / float(border_area)
                                # Wenn mehr als 60% des Rands grün sind, ist es das Logo (komplett von Röhre umschlossen).
                                # Der echte Vogel hat maximal ~30% grünen Rand, selbst wenn er an einer Röhre kratzt.
                                if green_ratio > 0.6:
                                    continue

                        # X-LOCK: Der Vogel bewegt sich in Flappy Bird niemals nach links oder rechts!
                        if bird_initial_x is not None:
                            # 100 Pixel Spielraum für Sprite-Rotationen und kleine Verschiebungen
                            if abs(bx - bird_initial_x) > 100:
                                continue 
                                
                        valid_bird_contours.append(cnt)
            
            if valid_bird_contours:
                bird_lost_frames = 0 # Reset
                # Nimm die GRÖSSTE rote Fläche in der rechten Bildschirmhälfte! 
                # Der echte Vogel ist viel größer als kleine rote Hintergrund-Logos.
                bird_cnt = max(valid_bird_contours, key=cv2.contourArea)
                bx, by, bw, bh = cv2.boundingRect(bird_cnt)
                bird_x, bird_y = bx, by
                
                last_bird_x, last_bird_y = bird_x, bird_y
                bird_found = True
                
                # Speichere die X-Position für immer
                if bird_initial_x is None:
                    bird_initial_x = bird_x
                    print(f"Vogel-X gelockt auf Safari-Fenster: {bird_initial_x}")
                    
                cv2.rectangle(screenshot, (bx, by), (bx+bw, by+bh), (255, 255, 255), 2)
                
                # HUD-Werte aktualisieren
                bird_y_val = f"{bird_y:.0f}"
                if 'prev_bird_y' in locals() and prev_bird_y is not None:
                    is_falling = bird_y >= prev_bird_y
                else:
                    is_falling = False
                status_text = "FALLEN" if is_falling else "STEIGEN"
                status_color = (0, 0, 255) if is_falling else (0, 255, 255)
            else:
                bird_lost_frames += 1
                
                # Wenn er den Vogel nur kurz verliert (z.B. Screen Flash bei Punktgewinn), nutze die alte Position!
                if bird_lost_frames <= 5 and last_bird_x is not None:
                    bird_x, bird_y = last_bird_x, last_bird_y
                    bird_found = True
                    bird_y_val = f"{bird_y:.0f}"
                    if 'prev_bird_y' in locals() and prev_bird_y is not None:
                        is_falling = bird_y >= prev_bird_y
                    else:
                        is_falling = False
                    status_text = "FALLEN" if is_falling else "STEIGEN"
                    status_color = (0, 0, 255) if is_falling else (0, 255, 255)
                    
                if bird_lost_frames > 30: # Nach ca. 1 Sekunde ohne Vogel
                    if bird_initial_x is not None:
                        print("Vogel verloren! X-Lock wird zurückgesetzt...")
                        bird_initial_x = None
                        bird_lost_frames = 0
                
            if bird_found:
                # Sammle alle Röhren-Teile rechts vom Vogel
                pipes = []
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    # Die Röhren-Spitzen sind mindestens 1000 Pixel groß.
                    if area > 1000:
                        x, y, w, h = cv2.boundingRect(cnt)
                        
                        # GEHEIMWAFFE: Die Form-Erkennung (Extent)!
                        # Röhren sind perfekte Rechtecke (Extent > 0.85).
                        # Büsche sind rund und wolkig (Extent ca. 0.6 - 0.75).
                        extent = area / float(w * h)
                        
                        # Gras-Filter 2: Gras ist horizontal (breiter als hoch) und immer unten!
                        # Ein Pause-Button oder ein Gebäude kann das Gras in Stücke hacken, 
                        # weshalb wir hier harte Kante zeigen müssen:
                        if w > h and y > screenshot.shape[0] * 0.5:
                            continue
                            
                        # w < 40% der Bildschirmbreite ignoriert das riesige, breite Gras am Boden (falls nicht schon gefiltert).
                        # x + w > bird_x behält die Röhre im Blick, solange der Vogel drin ist.
                        if (x + w) > bird_x and w < (screenshot.shape[1] * 0.4) and extent > 0.8:
                            pipes.append((x, y, w, h))
                            cv2.rectangle(screenshot, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        
                # Debugging für Röhrenanzahl
                if pipes:
                    # Sortiere Röhren nach ihrer X-Position (die am nächsten ist, steht vorne)
                    pipes.sort(key=lambda p: p[0])
                    nearest_x = pipes[0][0]
                    
                    # Nimm alle Röhren-Teile (oben und unten), die zu dieser X-Position gehören
                    nearest_pipes = [p for p in pipes if abs(p[0] - nearest_x) < 30]
                    
                    # Debug Print
                    if jump_needed == False: # Nur um nicht die Konsole zu überfluten
                        print(f"DEBUG - Erfasste nächste Röhren-Teile: {len(nearest_pipes)} Stück bei X={nearest_x}")
                        
                    # Wir sortieren alle Röhrenteile bei dieser X-Koordinate nach ihrer Y-Position (von oben nach unten).
                    pipes_sorted = sorted(nearest_pipes, key=lambda p: p[1])
                    
                    gap_y = 450 # Sicherer Fallback: Bildschirmmitte
                    
                    if len(pipes_sorted) >= 2:
                        # Wenn es mehrere Röhrenteile gibt, suchen wir die ECHTE Lücke.
                        # Das orange Logo zerschneidet Röhren (Abstand ca. 60px).
                        # Die echte Lücke zwischen oberer und unterer Röhre ist viel größer (z.B. > 150px).
                        max_gap = 0
                        best_gap_y = None
                        
                        for i in range(len(pipes_sorted) - 1):
                            p1 = pipes_sorted[i]
                            p2 = pipes_sorted[i+1]
                            
                            bottom_of_p1 = p1[1] + p1[3]
                            # OFFSET FÜR UNTERE RÖHRE: Die obere Kante hat ein sehr helles Highlight,
                            # das durch den Saturation-Filter rutscht. Wir korrigieren das künstlich um 50 Pixel nach oben!
                            top_of_p2 = p2[1] - 50
                            
                            gap_size = top_of_p2 - bottom_of_p1
                            if gap_size > max_gap:
                                max_gap = gap_size
                                mitte = bottom_of_p1 + gap_size / 2
                                best_gap_y = mitte + 30
                                
                        # Wenn wir eine Lücke > 100 Pixel finden, ist das die echte Flug-Lücke!
                        if max_gap > 100 and best_gap_y is not None:
                            gap_y = best_gap_y
                        # Sonst: gap_y bleibt beim sicheren Fallback (450)
                    # Bei nur 1 Röhrenteil oder unklarer Erkennung: NICHT RATEN!
                    # Einfach auf neutraler Höhe weiterfliegen.
                    
                    # SICHERHEITSKLAMMER: Nie an die Decke oder den Boden zielen!
                    gap_y = max(gap_y, 250)
                    gap_y = min(gap_y, 750)
                    
                    # Zeichne eine BLAUE Linie auf der Höhe, die der Bot anpeilt
                    cv2.line(screenshot, (0, int(gap_y)), (screenshot.shape[1], int(gap_y)), (255, 0, 0), 2)
                    
                    # LOGIK FÜR DEN SPRUNG:
                    target_y = gap_y 
                    target_y_val = f"{target_y:.0f}"
                    
                    if bird_y > target_y and is_falling:
                        current_time = time.time()
                        if current_time - last_jump_time > 0.15:
                            jump_needed = True
                            last_jump_time = current_time
                            print(f"Ziel-Höhe: {target_y:.0f} | Vogel-Höhe: {bird_y:.0f} -> SPRUNG!")
                
                # Speichere die Y-Koordinate für den nächsten Frame
                prev_bird_y = bird_y
                
                # NOTFALL-KLICK: Wenn 3 Sekunden lang kein Sprung, klicke einmal
                if time.time() - last_jump_time > 3.0:
                    jump_needed = True
                    last_jump_time = time.time()
                    print("NOTFALL-KLICK (Neustart)")
                    status_text = "NEUSTART!"
                    status_color = (0, 165, 255)
            
            if jump_needed:
                if status_text != "NEUSTART!":
                    status_text = "SPRUNG!"
                    status_color = (0, 255, 0)
                print(">>> SPRUNG!")
                
                pyautogui.mouseDown()
                time.sleep(0.05)
                pyautogui.mouseUp()
            
            # HUD zeichnen
            hud_x, hud_y, hud_w, hud_h = 10, 10, 280, 120
            if screenshot.shape[1] > hud_x + hud_w and screenshot.shape[0] > hud_y + hud_h:
                overlay = screenshot.copy()
                cv2.rectangle(overlay, (hud_x, hud_y), (hud_x + hud_w, hud_y + hud_h), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, screenshot, 0.4, 0, screenshot)
                cv2.rectangle(screenshot, (hud_x, hud_y), (hud_x + hud_w, hud_y + hud_h), (150, 150, 150), 1)

                cv2.putText(screenshot, f"Vogel-Y: {bird_y_val}", (hud_x + 15, hud_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(screenshot, f"Ziel-Y: {target_y_val}", (hud_x + 15, hud_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 1, cv2.LINE_AA)
                cv2.putText(screenshot, f"Notfall-Reset in: {reset_time_left:.1f}s", (hud_x + 15, hud_y + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 1, cv2.LINE_AA)
                cv2.putText(screenshot, f"Status: {status_text}", (hud_x + 15, hud_y + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2, cv2.LINE_AA)
            
            # Zeige das Debug-Fenster
            try:
                cv2.imshow("Bot Vision", screenshot)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Beenden-Taste 'q' gedrückt.")
                    break
            except Exception as e:
                pass
            
            # Loop drosseln (~60 FPS)
            time.sleep(0.016)
                
    print("Bot beendet.")

if __name__ == "__main__":
    try:
        start_bot()
    finally:
        pyautogui.mouseUp()
        try:
            cv2.destroyAllWindows()
        except:
            pass
