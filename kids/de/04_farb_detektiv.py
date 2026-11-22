# Mission 4: Farb-Detektiv! Halte bunte LEGO-Steine vor den Sensor.
#            Der Roboter sagt dir die Farbe und macht sein Licht genauso.
#
# So startest du:  uv run kids/de/04_farb_detektiv.py
# Du brauchst:     den Farb- und Abstandssensor (eingesteckt).
# Probier mal:     lass den Roboter vorwärts fahren, wenn er Grün sieht!

from lego_boost.kid import Roboter

with Roboter() as roboter:
    print("Zeig mir eine Farbe! (Strg+C zum Aufhoeren)")
    letzte = None
    for _ in range(200):
        farbe = roboter.farbe()
        if farbe != letzte and farbe != "nichts":
            print("Ich sehe", farbe.upper(), "!")
            roboter.licht(farbe)
            letzte = farbe
        roboter.warte(0.1)
