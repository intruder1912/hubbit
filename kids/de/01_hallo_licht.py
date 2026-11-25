# Mission 1: Lass das Licht vom Roboter die Farbe wechseln!
#
# So startest du:  uv run kids/de/01_hallo_licht.py
# Probier mal:     ändere "rot" in "blau" oder "gelb", oder nimm mehr Farben dazu.

from hubbit.kid import Roboter

with Roboter() as roboter:
    roboter.licht("rot")
    roboter.warte(1)
    roboter.licht("gelb")
    roboter.warte(1)
    roboter.licht("gruen")
    roboter.warte(1)
