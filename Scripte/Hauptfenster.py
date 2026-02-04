# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QMainWindow, QPushButton, QGroupBox, QGridLayout, QWidget, QTextEdit, QLineEdit
from PyQt5.QtCore import pyqtSignal
from Scripte import Bekanntmachungen, Infosystem
import threading


class Anzeigen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ergänzungsprogramm Insolvenzen")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QGridLayout(central_widget)

        ausgabe = Ausgabe()
        self.layout.addWidget(Bekanntmachung(ausgabe=ausgabe), 0, 0)
        self.layout.addWidget(GrpInfstm(ausgabe=ausgabe), 1, 0)
        self.layout.addWidget(ausgabe, 2, 0)

        self.setLayout(self.layout)
        self.showMaximized()


class Bekanntmachung(QGroupBox):
    def __init__(self, ausgabe):
        super().__init__()
        self.ausgabe = ausgabe
        self.setTitle("Bekanntmachungen")
        self.layout = QGridLayout()
        self.einrichten()
        self.setLayout(self.layout)

    def einrichten(self):
        pb_bkm_import = QPushButton("Bekanntmachungen auslesen")
        pb_bkm_import.clicked.connect(lambda: self.auslesen())
        self.layout.addWidget(pb_bkm_import, 0, 0)

        pb_bkm_sicht = QPushButton("Bekanntmachungen ansehen")
        pb_bkm_sicht.clicked.connect(lambda: self.bkm_ansehen())
        self.layout.addWidget(pb_bkm_sicht, 0, 1)

        pb_vzk_a = QPushButton("Vollzähligkeit A-Meldungen")
        pb_vzk_a.clicked.connect(lambda: self.vzk_a())
        self.layout.addWidget(pb_vzk_a, 0, 2)

    def auslesen(self):
        thread = threading.Thread(target=self.auslesen_thread, daemon=True)
        thread.start()

    def auslesen_thread(self):
        Bekanntmachungen.Auslesen(self.ausgabe)

    def bkm_ansehen(self):
        pass

    def vzk_a(self):
        pass


class GrpInfstm(QGroupBox):
    def __init__(self, ausgabe):
        super().__init__()
        self.setTitle("Infosystem")
        self.ausgabe = ausgabe
        self.layout = QGridLayout()
        self.le_monat = QLineEdit()
        self.le_jahr = QLineEdit()
        self.einrichten()
        self.setLayout(self.layout)

    def einrichten(self):
        pb_ifs_erstellen = QPushButton("Daten erstellen")
        pb_ifs_erstellen.clicked.connect(lambda: self.erstellen())
        self.layout.addWidget(pb_ifs_erstellen, 0, 0)

        self.le_monat.setPlaceholderText("Berichtsmonat angeben")
        self.layout.addWidget(self.le_monat, 0, 1)

        self.le_jahr.setPlaceholderText("Berichtsjahr angeben")
        self.layout.addWidget(self.le_jahr, 0, 2)

    def erstellen(self):
        app = Infosystem
        app.Infosystem(self.le_monat.text(), self.le_jahr.text(), self.ausgabe)


class Ausgabe(QGroupBox):
    # Signal: garantiert Thread-sicher
    append_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setTitle("Ausgabe")
        self.layout = QGridLayout()
        self.txt_edit = QTextEdit()
        self.txt_edit.setReadOnly(True)

        # Signal in GUI-Thread an QTextEdit.append binden
        self.append_signal.connect(self.txt_edit.append)

        self.einrichten()
        self.setLayout(self.layout)

    def einrichten(self):
        self.layout.addWidget(self.txt_edit)

    # Thread-sichere Ausgabe-Funktion
    def append(self, text: str):
        self.append_signal.emit(text)
