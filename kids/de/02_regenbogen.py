# Mission 2: Regenbogen-Party! Das Licht zeigt 3-mal alle Farben.
#
# So startest du:  uv run kids/de/02_regenbogen.py
# Probier mal:     mach es schneller: ändere 0.3 in 0.1, oder ändere 3 in 10.

from hubbit.kid import Roboter

regenbogen = ["rot", "orange", "gelb", "gruen", "blau", "lila"]

with Roboter() as roboter:
    for runde in range(3):
        print("Runde", runde + 1)
        for farbe in regenbogen:
            roboter.licht(farbe)
            roboter.warte(0.3)
