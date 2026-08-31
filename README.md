# 🦅 Flappy Bot (Computer Vision Auto-Player)

Ein in Python geschriebener, vollautomatischer Bot, der Flappy Bird Klone (im Browser) selbstständig über Computer Vision (OpenCV) und Bilderkennung spielt. Er benötigt keine API oder direkten Zugriff auf den Spielcode, sondern "sieht" das Spiel exakt so, wie ein Mensch es tun würde!

## ✨ Features

- **👀 Echtzeit Computer-Vision:** Liest den Bildschirm mit `mss` (ultraschnell) aus.
- **🐦 HSV-Farb-Tracking:** Erkennt den Vogel und die Röhren völlig dynamisch anhand von Farbwerten (rot/orange für den Vogel, hellgrün für die Röhren), statt sich auf statische Pixel-Templates zu verlassen.
- **🎯 Dynamische Lücken-Berechnung:** Findet selbstständig die obere und untere Röhre, berechnet die genaue Durchflug-Mitte und zielt auf den "Sweet-Spot" (+35 Pixel unter der Mitte), um den starken Sprung abzufangen.
- **🧩 Logo-Toleranz:** Ignoriert störende Werbe-Logos (z. B. "Crispy Coop"), die die Röhren in der Mitte durchschneiden, und erkennt auch abgetrennte kleine Röhrenspitzen.
- **⚡️ Zero Input Lag:** Nutzt direkte Mausklicks (`pyautogui.click()`) und deaktiviert die automatische PyAutoGUI-Pause für blitzschnelle Latenzen.

## 🛠 Voraussetzungen

Das Skript wurde für macOS optimiert, läuft aber auch auf anderen Systemen (mit kleinen Anpassungen an der Bildschirm-Skalierung).

1. **Python 3.10+**
2. **Abhängigkeiten installieren:**
   ```bash
   pip install opencv-python numpy mss pyautogui
   ```
3. **Bedienungshilfen (macOS):**
   Damit PyAutoGUI Mausklicks simulieren darf, musst du deinem Terminal (oder der IDE) unter macOS die Berechtigung erteilen:
   *Systemeinstellungen > Datenschutz & Sicherheit > Bedienungshilfen*

## 🚀 Benutzung

1. Öffne das Spiel in einem Browser (z. B. Safari) auf dem **linken** Monitor oder der linken Bildschirmhälfte.
2. Starte den Bot im Terminal:
   ```bash
   python bot.py
   ```
3. Du hast 3 Sekunden Zeit, um dein Browser-Fenster in den Vordergrund zu holen.
4. **WICHTIG:** Platziere deinen **Mauszeiger** irgendwo über dem Spiel-Fenster! Der Bot simuliert Mausklicks (Linksklick) zum Springen, daher muss die Maus über dem Canvas des Spiels liegen.
5. Das "Bot Vision" Fenster öffnet sich. Hier siehst du live, wie der Bot das Spiel interpretiert (Masken, Ziel-Linien, Boxen).
6. Zum **Abbrechen** wähle das "Bot Vision" Fenster aus und drücke die Taste `q` auf der Tastatur (oder brich das Skript im Terminal mit `Ctrl+C` ab).

## 🧠 Wie es funktioniert (Die Logik)

1. **Vogelerkennung:** Das Skript konvertiert den Bildschirm in den HSV-Farbraum und filtert nach den typischen Rot/Orange-Werten des Vogels. Die größte zusammenhängende rote Fläche wird als Vogel markiert.
2. **Röhrenerkennung:** Das gleiche passiert für das Hellgrün der Röhren. Alle grünen Flächen **rechts** vom Vogel werden als kommende Hindernisse erfasst.
3. **Zielen:** Der Bot filtert die nächste Röhren-Paarung heraus. Er sucht den tiefsten Punkt der oberen Röhre und den höchsten Punkt der unteren Röhre.
4. **Springen:** Sobald der Vogel (Y-Koordinate) tiefer fällt als der berechnete "Sweet-Spot" in der Lücke, löst der Bot einen Linksklick aus. Ein Cooldown verhindert, dass er zu schnell hintereinander klickt.

## 📝 Lizenz

Open-Source MIT