# -*- coding: utf-8 -*-

from Scripte import Hauptfenster
import sys
from PyQt5.QtWidgets import QApplication

# TODO: Grafische Nutzeroberfläche;
## Vollzähligkeitskontrolle A-Meldungen
## Gesamtdatensatz für monatliche und jährliche A-Meldungen


if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenster = Hauptfenster.Anzeigen()
    fenster.show()
    sys.exit(app.exec_())

