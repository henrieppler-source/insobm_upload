# -*- coding: utf-8 -*-

import configparser


def daten_auslesen(datei):
    """
    config.ini auslesen
    :param datei: Config-Datei
    :return: gesuchter Wert
    """
    config = configparser.ConfigParser()
    config.read(datei)
    print(config.sections())
    return config


def schreiben(datei, config, sektion, option, wert):
    """
    config-Datei beschreiben/aktualisieren
    :type sektion: Sektion in der Config-Datei
    :type config: Pfad der Config-Datei
    :type option: Option in der Config-Datei
    :type wert: Wert für die Option
    :return: Nothing
    """

    config.set(section=sektion, option=option, value=wert)
    with open(datei, "w") as configfile:
        config.write(configfile)
