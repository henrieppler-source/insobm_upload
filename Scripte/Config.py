# -*- coding: utf-8 -*-

import configparser
import os


def daten_auslesen(datei):
    """
    Config-Datei lesen
    """
    config = configparser.ConfigParser()
    if os.path.exists(datei):
        config.read(datei, encoding="utf-8")
    return config


def schreiben(datei, config, sektion, option, wert):
    """
    Config-Datei beschreiben/aktualisieren

    :param datei: Pfad der Config-Datei
    :param config: ConfigParser-Objekt oder None
    :param sektion: Sektion in der Config-Datei
    :param option: Option in der Config-Datei
    :param wert: Wert für die Option
    """

    # Falls kein Config-Objekt übergeben wurde -> neu einlesen
    if config is None:
        config = daten_auslesen(datei)

    # Sektion ggf. anlegen
    if not config.has_section(sektion):
        config.add_section(sektion)

    # Wert setzen
    config.set(sektion, option, wert)

    # Datei schreiben
    with open(datei, "w", encoding="utf-8") as configfile:
        config.write(configfile)
