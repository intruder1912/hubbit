# Mission 5: Fernsteuerung! Tippe einen Buchstaben und drücke Enter.
#
#   w = vorwärts   s = rückwärts   a = links   d = rechts   q = aufhören
#
# So startest du:  uv run kids/de/05_fernsteuerung.py
# Probier mal:     nimm einen neuen Buchstaben dazu, z.B. "l" für eine Lichtshow!

from lego_boost.kid import Roboter

with Roboter() as roboter:
    while True:
        taste = input("Befehl (w/a/s/d, q zum Aufhoeren): ").strip().lower()
        if taste == "w":
            roboter.vorwaerts(0.5)
        elif taste == "s":
            roboter.rueckwaerts(0.5)
        elif taste == "a":
            roboter.links(0.3)
        elif taste == "d":
            roboter.rechts(0.3)
        elif taste == "q":
            break
        else:
            print("Den kenne ich nicht!")
