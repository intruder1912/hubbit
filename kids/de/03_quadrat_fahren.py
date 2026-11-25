# Mission 3: Fahr ein Quadrat!
#
# So startest du:  uv run kids/de/03_quadrat_fahren.py
# Vorsicht:        stell den Roboter auf den Boden, mit viel Platz rundherum.
# Probier mal:     schaffst du ein Dreieck? Oder einen Zickzack?
#                  (rechts() ist eine Vierteldrehung. rechts(0.2) dreht weniger,
#                  rechts(0.7) dreht ungefähr eine halbe Runde.)

from hubbit.kid import Roboter

with Roboter() as roboter:
    for seite in range(4):
        print("Seite", seite + 1)
        roboter.licht("blau")
        roboter.vorwaerts(1)
        roboter.licht("gelb")
        roboter.rechts()
