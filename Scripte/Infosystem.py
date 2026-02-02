# -*- coding: utf-8 -*-

import pandas as pd
from Scripte import Import, Bedingungen
import numpy as np


class Infosystem:
    def __init__(self, bm, bj, ausgabe):
        # plausibles Einzelmaterial holen
        self.df_aj = Import.csv(r"./Eingang/Eingabe-AJ.csv")

        # leere Zellen durch den Wert 0 füllen
        self.df_aj.fillna(0)

        # Klassen variablen festlegen
        self.bm = bm
        self.bj = bj
        self.ausgabe = ausgabe
        self.bzr = '{0}-{1}'.format(self.bj, self.bm)
        self.ags = ['04', '04011', '04012']
        self.gericht = ['04', '041101', '041102']
        self.ausgabe.txt_edit.append(f"Erstellung der Infosystem-Tabelle beginnt...")
        # Bedingungen festlegen
        # -- Bedingung für Unternehmen
        self.bed_unt = Bedingungen.unternehmen(self.df_aj)
        # -- Bedingung für Verbraucher
        self.bed_ver = Bedingungen.verbraucher(self.df_aj)
        # -- Bedingung für den Berichtszeitraum
        self.bed_bzr = Bedingungen.berichtszeitraum(self.df_aj, str(self.bm), str(self.bj))
        # -- eröffnet
        self.bed_eroEFf = Bedingungen.eroeffnet(self.df_aj)
        # -- mangels Masse abgewiesen
        self.bed_mma = Bedingungen.mangels_masse(self.df_aj)
        # -- Schuldenbereinigungsplan angenommen
        self.bed_sba = Bedingungen.schuldenbereinigungsplan(self.df_aj)

        if self.bm == '12':
            self.tab_52411_55_01()
            self.tab_52411_66_01()
            self.tab_52411_00_01()
            self.tab_52411_01_01()
            self.tab_52411_02_01()
            self.tab_52411_03_01()
            self.tab_52411_00_02()
            self.tab_52411_00_03()
            self.tab_52411_00_04()
            self.tab_52411_00_05()
            self.tab_52411_00_06()

        elif self.bm == '06' or self.bm == '6':
            self.tab_52411_55_01()
            self.tab_52411_66_01()
        else:
            self.tab_52411_55_01()
        self.ausgabe.txt_edit.append(f"... Erstellung abgeschlossen")

    def tab_52411_55_01(self):
        """
        Tabelle '52411-55-01 Insolvenzen an den Amtsgerichten (Monatszahlen)'
        :return:
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 55411_55_01 wird erstellt")
        berichtszeitraum = '{0}-{1}'.format(self.bj, self.bm)
        i = 0
        zeitraum = (self.df_aj["EF7"].apply(int) == int(self.bm)) & (self.df_aj["EF6"] == self.bj) & \
                   (self.df_aj["EFSPAET"] != '1')
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            bed_ags = (self.df_aj['EF42'].str.startswith(ags))
            daten = {
                '1': ['52411-55-01',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj['EF1'].where(zeitraum & bed_gericht).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_eroEFf).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_mma).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_sba).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & bed_ags).count()
                      ],
                '2': ['52411-55-01',
                      berichtszeitraum,
                      ags,
                      2,
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_unt).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_unt & self.bed_eroEFf).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_unt & self.bed_mma).count(),
                      'x',
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_unt & bed_ags).count()
                      ],
                '3': ['52411-55-01',
                      berichtszeitraum,
                      ags,
                      3,
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_ver).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_ver & self.bed_eroEFf).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_ver & self.bed_mma).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_ver & self.bed_sba).count(),
                      self.df_aj['EF1'].where(zeitraum & bed_gericht & self.bed_ver & bed_ags).count()
                      ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_66_01(self):
        """
        Erstellung der Tabelle '52411-06-01 Insolvenzen an den Amtsgerichten (Halbjahresergebnisse)
        Aufbau:
            Spalten:
                Schuldner ; Insgesamt ; eröffnet ; mangels Masse abgewiesen ; Schuldenbereinigungsplan
                angenommen ; und zwar mit Sitz im jeweiligen Gebiet ; voraussichtlichen Forderungen in 1000 Euro
            Zeilen:
                04 Land Bremen - Insgesamt; darunter Unternehmen ; darunter Verbraucher
                04011 Stadt Bremen - Insgesamt; darunter Unternehmen ; darunter Verbraucher
                04012 Stadt Bremerhaven - Insgesamt ; darunter Unternehmen ; darunter Verbraucher
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_66_01 wird erstellt")
        zeitraum = None
        berichtsmonat = None
        if self.bm == '12':
            zeitraum = (self.df_aj["EF7"].apply(int).isin([7, 8, 9, 10, 11, 12])) & (self.df_aj["EF6"] == self.bj) & \
                       (self.df_aj["EFSPAET"] != '1')
            berichtsmonat = 'H2'
        elif self.bm == '06':
            zeitraum = (self.df_aj["EF7"].apply(int).isin([1, 2, 3, 4, 5, 6])) & (self.df_aj["EF6"] == self.bj) & \
                       (self.df_aj["EFSPAET"] != '1')
            berichtsmonat = 'H1'
        berichtszeitraum = '{0}-{1}'.format(self.bj, berichtsmonat)
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            bed_ags = (self.df_aj['EF42'].str.contains(ags))
            daten = {
                '1': ['52411-66-01',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & self.bed_eroEFf).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & self.bed_mma).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & self.bed_sba).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags).count(),
                      int(round(self.df_aj["EF20"].where(zeitraum & bed_gericht, 0).apply(int).sum() / 1000, 0))
                      ],
                '2': ['52411-66-01',
                      berichtszeitraum,
                      ags,
                      2,
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & self.bed_eroEFf).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & self.bed_mma).count(),
                      'x',
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags).count(),
                      int(round(self.df_aj["EF20"].where(zeitraum & self.bed_unt & bed_gericht, 0).apply(
                          int).sum() / 1000, 0))
                      ],
                '3': ['52411-66-01',
                      berichtszeitraum,
                      ags,
                      3,
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht & self.bed_eroEFf).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht & self.bed_mma).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht & self.bed_sba).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht & bed_ags).count(),
                      int(round(self.df_aj["EF20"].where(zeitraum & self.bed_ver & bed_gericht, 0).apply(
                          int).sum() / 1000, 0))
                      ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_00_01(self):
        """
        Erstellung der Tabelle '52411-06-01 Insolvenzen an den Amtsgerichten (Jahreszahlen)
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_00_01 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')

        berichtszeitraum = '{0}'.format(self.bj)
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            bed_ags = (self.df_aj['EF42'].str.contains(ags))

            daten = {
                '1': ['52411-00-01',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & self.bed_eroEFf).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & self.bed_mma).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & self.bed_sba).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & bed_gericht).count(),
                      ],
                '2': ['52411-00-01',
                      berichtszeitraum,
                      ags,
                      2,
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & self.bed_eroEFf).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & self.bed_mma).count(),
                      'x',
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & bed_gericht).count(),
                      ],
                '3': ['52411-00-01',
                      berichtszeitraum,
                      ags,
                      3,
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht & self.bed_eroEFf).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht & self.bed_mma).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht & self.bed_sba).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_ver & bed_gericht & bed_ags & bed_gericht).count(),
                      ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_01_01(self):
        """
        Erstellung der Tabelle '52411-06-01 Insolvenzen Insgesamt'
        Hinweis: Bremen und Bremerhaven werden nur nach AGS gEFiltert, nicht nach Gericht
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_01_01 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')
        berichtszeitraum = '{0}'.format(self.bj)
        i = 0
        bed_ags = None
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            if not i == 0:
                bed_ags = (self.df_aj['EF42'].str.contains(ags))
                bed_gericht = bed_ags
            elif i == 0:
                bed_ags = bed_gericht
            daten = {
                '1': ['52411-01-01',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & bed_ags & bed_gericht).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_ags & bed_gericht & self.bed_eroEFf).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_ags & bed_gericht & self.bed_mma).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_ags & bed_gericht & self.bed_sba).count(),
                      self.df_aj["EF15"].replace('', 0).where(zeitraum & bed_ags &
                                                              bed_gericht, 0).fillna(0).astype(int).sum(),
                      int(round(self.df_aj["EF20"].where(zeitraum & bed_ags & bed_gericht, 0).apply(
                          int).sum() / 1000, 0))
                      ],
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_02_01(self):
        """
        Erstellung der Tabelle '52411-02-01 Unternehmensinsolvenzen'
        Hinweis: Bremen und Bremerhaven werden nur nach AGS gEFiltert, nicht nach Gericht
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_02_01 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')

        berichtszeitraum = '{0}'.format(self.bj)
        bed_ags = None
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            if not i == 0:
                bed_ags = (self.df_aj['EF42'].str.contains(ags))
                bed_gericht = bed_ags
            elif i == 0:
                bed_ags = bed_gericht
            daten = {
                '1': ['52411-02-01',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & bed_ags & self.bed_unt & bed_gericht).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_ags & self.bed_unt & bed_gericht &
                                              self.bed_eroEFf).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_ags & self.bed_unt & bed_gericht &
                                              self.bed_mma).count(),
                      self.df_aj["EF15"].replace('', 0).where(zeitraum & bed_ags &
                                                              bed_gericht, 0).fillna(0).astype(int).sum(),
                      int(round(self.df_aj["EF20"].where(zeitraum & bed_ags & self.bed_unt & bed_gericht, 0).apply(
                          int).sum() / 1000, 0))
                      ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_03_01(self):
        """
        Erstellung der Tabelle '52411-03-01 Insolvenzen übriger Schuldner'
        Hinweis: Bremen und Bremerhaven werden nur nach AGS gEFiltert, nicht nach Gericht
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_03_01 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')

        berichtszeitraum = '{0}'.format(self.bj)
        bed_ags = None
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            if not i == 0:
                bed_ags = (self.df_aj['EF42'].str.contains(ags))
                bed_gericht = bed_ags
            elif i == 0:
                bed_ags = bed_gericht

            daten = {
                '1': ['52411-03-01',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              ((self.df_aj['EF12'].isin(['01', '12', '13'])) |
                                               (self.df_aj['EF49N'].isin(['1', '2'])))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF49N'].isin(['2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF49N'].isin(['2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF49N'].isin(['2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_sba &
                                              (self.df_aj['EF49N'].isin(['2']))).count(),
                      int(round(self.df_aj["EF20"].where(zeitraum & bed_gericht & bed_ags & (self.df_aj['EF49N'].isin(
                          ['2'])), 0).apply(int).sum() / 1000, 0)),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              ((self.df_aj['EF12'].isin(['13'])) |
                                               (self.df_aj['EF49N'].isin(['1'])))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF12'].isin(['01', '12']))).count()
                      ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_00_02(self):
        """
        Erstellung der Tabelle '52411-00-02' Unternehmensinsolvenzen nach Wirtschaftsbereichen
        Hinweis:
        - Bremen und Bremerhaven werden nur nach AGS gEFiltert, nicht nach Gericht.
        - Die WZ wird erst ab eine Länge von 5 Zeichen berücksichtigt
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_00_02 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')
        laeng_wz = (self.df_aj["EF13"].str.len() >= 5)

        berichtszeitraum = '{0}'.format(self.bj)
        bed_ags = None
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            if not i == 0:
                bed_ags = (self.df_aj['EF42'].str.contains(ags))
                bed_gericht = bed_ags
            elif i == 0:
                bed_ags = bed_gericht
            daten = {
                '1': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'A')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF13"].str[:1] == 'A')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF13"].str[:1] == 'A')).count()
                      ],
                '2': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      2,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'B')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'B')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'B')).count()
                      ],
                '3': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      3,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'C')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'C')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'C')).count()
                      ],
                '4': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      4,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'D')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'D')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'D')).count()
                      ],
                '5': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      5,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'E')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'E')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'E')).count()
                      ],
                '6': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      6,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'F')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'F')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'F')).count()
                      ],
                '7': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      7,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'G')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'G')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'G')).count()
                      ],
                '8': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      8,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'H')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'H')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'H')).count()
                      ],
                '9': ['52411-00-02',
                      berichtszeitraum,
                      ags,
                      9,
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'I')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'I')).count(),
                      self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF13"].str[:1] == 'I')).count()
                      ],
                '10': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       10,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'J')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'J')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'J')).count()
                       ],
                '11': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       11,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'K')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'K')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'K')).count()
                       ],
                '12': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       12,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'L')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'L')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'L')).count()
                       ],
                '13': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       13,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'M')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'M')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'M')).count()
                       ],
                '14': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       14,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'N')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'N')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'N')).count()
                       ],
                '15': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       15,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'O')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'O')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'O')).count()
                       ],
                '16': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       16,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'P')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'P')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'P')).count()
                       ],
                '17': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       17,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'Q')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'Q')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'Q')).count()
                       ],
                '18': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       18,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'R')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'R')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'R')).count()
                       ],
                '19': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       19,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'S')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'S')).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1] == 'S')).count()
                       ],
                '20': ['52411-00-02',
                       berichtszeitraum,
                       ags,
                       20,
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & bed_ags &
                                               (self.df_aj["EF13"].str[:1].isin(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                                                                                 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
                                                                                 'Q', 'R', 'S']))).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_eroEFf & bed_ags &
                                               (self.df_aj["EF13"].str[:1].isin(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                                                                                 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
                                                                                 'Q', 'R', 'S']))).count(),
                       self.df_aj["EF1"].where(zeitraum & laeng_wz & bed_gericht & self.bed_mma & bed_ags &
                                               (self.df_aj["EF13"].str[:1].isin(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                                                                                 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
                                                                                 'Q', 'R', 'S']))).count()
                       ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_00_03(self):
        """
        Erstellung der Tabelle '52411-00-03 Unternehmensinsolvenzen nach Rechtsform'
        Hinweis: Bremen und Bremerhaven werden nur nach AGS gEFiltert, nicht nach Gericht
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_00_03 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')

        berichtszeitraum = '{0}'.format(self.bj)
        bed_ags = None
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            if not i == 0:
                bed_ags = (self.df_aj['EF42'].str.contains(self.ags[i]))
                bed_gericht = bed_ags
            elif i == 0:
                bed_ags = bed_gericht

            daten = {
                '1': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"] == '02')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & self.bed_eroEFf & bed_ags &
                                              (self.df_aj["EF12"] == '02')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & self.bed_mma & bed_ags &
                                              (self.df_aj["EF12"] == '02')).count()
                      ],
                '2': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      2,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"].isin(['03', '04', '05', '06']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF12"].isin(['03', '04', '05', '06']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF12"].isin(['03', '04', '05', '06']))).count()
                      ],
                '3': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      3,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"] == '05')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF12"] == '05')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF12"] == '05')).count()
                      ],
                '4': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      5,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"] == '06')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF12"] == '06')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF12"] == '06')).count()
                      ],
                '5': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      5,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"].isin(['09', '17']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF12"].isin(['09', '17']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF12"].isin(['09', '17']))).count()
                      ],
                '6': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      6,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"] == '09')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF12"] == '09')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF12"] == '09')).count()
                      ],
                '7': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      7,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"] == '17')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF12"] == '17')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF12"] == '17')).count()
                      ],
                '8': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      8,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"] == '08')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF12"] == '08')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF12"] == '08')).count()
                      ],
                '9': ['52411-00-03',
                      berichtszeitraum,
                      ags,
                      9,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj["EF12"] == '10')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj["EF12"] == '10')).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj["EF12"] == '10')).count()
                      ],
                '10': ['52411-00-03',
                       berichtszeitraum,
                       ags,
                       10,
                       self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                               (self.df_aj["EF12"].isin(['11', '16']))).count(),
                       self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                               (self.df_aj["EF12"].isin(['11', '16']))).count(),
                       self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                               (self.df_aj["EF12"].isin(['11', '16']))).count()
                       ],
                '11': ['52411-00-03',
                       berichtszeitraum,
                       ags,
                       11,
                       self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                               (self.df_aj["EF12"].isin(['02', '03', '04', '05', '06', '08', '09', '10',
                                                                         '11', '16', '17']))).count(),
                       self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                               (self.df_aj["EF12"].isin(['02', '03', '04', '05', '06', '08', '09', '10',
                                                                         '11', '16', '17']))).count(),
                       self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                               (self.df_aj["EF12"].isin(['02', '03', '04', '05', '06', '08', '09', '10',
                                                                         '11', '16', '17']))).count()
                       ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_00_04(self):
        """
        Erstellung der Tabelle '52411-00-04 Unternehmensinsolvenzen nach dem Alter des Unternehmens'
        Hinweis: Bremen und Bremerhaven werden nur nach AGS gEFiltert, nicht nach Gericht
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_00_04 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')

        bed_unternehmen = (self.df_aj["EF12"].isin(['02', '03', '04', '05', '06', '08', '09', '10',
                                                    '11', '16', '17']))

        berichtszeitraum = '{0}'.format(self.bj)
        bed_ags = None
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            if not i == 0:
                bed_ags = (self.df_aj['EF42'].str.contains(ags))
                bed_gericht = bed_ags
            elif i == 0:
                bed_ags = bed_gericht

            daten = {
                '1': ['52411-00-04',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags &
                                              (self.df_aj['EF60'].isin(['1', '2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF60'].isin(['1', '2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF60'].isin(['1', '2']))).count()
                      ],
                '2': ['52411-00-04',
                      berichtszeitraum,
                      ags,
                      2,
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags &
                                              (self.df_aj['EF60'].isin(['1']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF60'].isin(['1']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF60'].isin(['1']))).count()
                      ],
                '3': ['52411-00-04',
                      berichtszeitraum,
                      ags,
                      3,
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags &
                                              (self.df_aj['EF60'].isin(['3']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF60'].isin(['3']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF60'].isin(['3']))).count()
                      ],
                '4': ['52411-00-04',
                      berichtszeitraum,
                      ags,
                      4,
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags &
                                              (self.df_aj['EF60'].isin(['0']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF60'].isin(['0']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF60'].isin(['0']))).count()
                      ],
                '5': ['52411-00-04',
                      berichtszeitraum,
                      ags,
                      5,
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags &
                                              (self.df_aj['EF60'].isin(['0', '1', '2', '3']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF60'].isin(['0', '1', '2', '3']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_unternehmen & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF60'].isin(['0', '1', '2', '3']))).count()
                      ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_00_05(self):
        """
        Erstellung der Tabelle '52411-00-05 Unternehmensinsolvenzen nach der Zahl der Arbeitnehmer'
        Hinweis: Bremen und Bremerhaven werden nur nach AGS gEFiltert, nicht nach Gericht
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_00_05 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')

        berichtszeitraum = '{0}'.format(self.bj)
        bed_ags = None
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            if not i == 0:
                bed_ags = (self.df_aj['EF42'].str.contains(ags))
                bed_gericht = bed_ags
            elif i == 0:
                bed_ags = bed_gericht

            daten = {
                '1': ['52411-00-05',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags &
                                              (self.df_aj['EF76'].isin(['1']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF76'].isin(['1']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF76'].isin(['1']))).count()
                      ],
                '2': ['52411-00-05',
                      berichtszeitraum,
                      ags,
                      2,
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags &
                                              (self.df_aj['EF76'].isin(['2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF76'].isin(['2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF76'].isin(['2']))).count()
                      ],
                '3': ['52411-00-05',
                      berichtszeitraum,
                      ags,
                      3,
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags &
                                              (self.df_aj['EF76'].isin(['3']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF76'].isin(['3']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF76'].isin(['3']))).count()
                      ],
                '4': ['52411-00-05',
                      berichtszeitraum,
                      ags,
                      4,
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags &
                                              (self.df_aj['EF76'].isin(['4']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF76'].isin(['4']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF76'].isin(['4']))).count()
                      ],
                '5': ['52411-00-05',
                      berichtszeitraum,
                      ags,
                      5,
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags &
                                              (self.df_aj['EF76'].isin(['5', '6', '7']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF76'].isin(['5', '6', '7']))).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF76'].isin(['5', '6', '7']))).count()
                      ],
                '6': ['52411-00-05',
                      berichtszeitraum,
                      ags,
                      6,
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags &
                                              ((self.df_aj['EF76'].isin(['0', ''])) | self.df_aj['EF76'].isna())).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_eroEFf &
                                              ((self.df_aj['EF76'].isin(['0', ''])) | self.df_aj['EF76'].isna())).count(),
                      self.df_aj["EF1"].where(zeitraum & self.bed_unt & bed_gericht & bed_ags & self.bed_mma &
                                              ((self.df_aj['EF76'].isin(['0', ''])) | self.df_aj['EF76'].isna())).count(),
                      ]
            }
            i += 1
            self.ausgeben(daten=daten)

    def tab_52411_00_06(self):
        """
        Erstellung der Tabelle '52411-00-06 Insolvenzen nach der Höhe der voraussichtlichen Forderungen'
        Hinweis: Bremen und Bremerhaven werden nur nach AGS gEFiltert, nicht nach Gericht
        :return: None
        """
        self.ausgabe.txt_edit.append(f"\nTabelle 52411_00_06 wird erstellt")
        zeitraum = (self.df_aj["EF6"] == self.bj) & (self.df_aj["EFSPAET"] != '1')

        berichtszeitraum = '{0}'.format(self.bj)
        bed_ags = None
        i = 0
        for ags in self.ags:
            bed_gericht = (self.df_aj['EF3'].str.contains(self.gericht[i]))
            if not i == 0:
                bed_ags = (self.df_aj['EF42'].str.contains(ags))
                bed_gericht = bed_ags
            elif i == 0:
                bed_ags = bed_gericht

            daten = {
                '1': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      1,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF61'].isin(['1']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['1']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['1']))).count()
                      ],
                '2': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      2,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF61'].isin(['2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['2']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['2']))).count()
                      ],
                '3': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      3,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF61'].isin(['3']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['3']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['3']))).count()
                      ],
                '4': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      4,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF61'].isin(['4']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['4']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['4']))).count()
                      ],
                '5': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      5,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF61'].isin(['5']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['5']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['5']))).count()
                      ],
                '6': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      6,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF61'].isin(['6']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['6']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['6']))).count()
                      ],
                '7': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      7,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF61'].isin(['7']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['7']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['7']))).count()
                      ],
                '8': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      8,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags &
                                              (self.df_aj['EF61'].isin(['8']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['8']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['8']))).count()
                      ],
                '9': ['52411-00-06',
                      berichtszeitraum,
                      ags,
                      9,
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & (self.df_aj['EF61'].isin(
                          ['1', '2', '3', '4', '5', '6', '7', '8']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_eroEFf &
                                              (self.df_aj['EF61'].isin(['1', '2', '3', '4', '5', '6',
                                                                        '7', '8']))).count(),
                      self.df_aj["EF1"].where(zeitraum & bed_gericht & bed_ags & self.bed_mma &
                                              (self.df_aj['EF61'].isin(['1', '2', '3', '4', '5', '6',
                                                                        '7', '8']))).count()
                      ]
            }
            i += 1
            self.ausgeben(daten=daten)


    @staticmethod
    def convert_element(element):
        if element == 0:
            return '-'
        return str(element)

    def ausgeben(self, daten):
        for zeile in daten.values():
            self.ausgabe.txt_edit.append(f"{';'.join(map(self.convert_element, zeile))}")
