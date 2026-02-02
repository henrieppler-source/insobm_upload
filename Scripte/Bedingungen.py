# -*- coding: utf-8 -*-

"""
Hier werden sämtliche Bedingungen aufgelistet, um Fehler bei Auswertungen zu minimieren
"""


def unternehmen(df):
    """
    Bedingung zur Ermittlung der Unternehmen
    :param df: Dataframe
    :return: Bedingung
    """
    bedingung = (df['EF12'].isin(['02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '16', '17']))
    return bedingung


def verbraucher(df):
    """
    Bedingung zur Ermittlung der Verbraucher
    :param df: Dataframe
    :return: Bedingung
    """
    bedingung = (df['EF49N'] == '2')
    return bedingung


def berichtszeitraum(df, bj, bm):
    """
    Bedingung zur Ermittlung des Berichtszeitraums
    :param bm: Berichtsmonat
    :param bj: Berichtsjahr
    :param df: Dataframe
    :return: Bedingung
    """
    bedingung = (df['EF7'] == bm) & (df['EFSPAET'] != '1') & (df['EF6'] == bj)
    return bedingung


def eroeffnet(df):
    """
    Bedingung zur Ermittlung der eröffneten Verfahren
    :param df: Dataframe
    :return: Bedingung
    """
    bedingung = (df['EF16'] == '1')
    return bedingung


def mangels_masse(df):
    """
    Bedingung zur Ermittlung der mangels Masse abgewiesenen Verfahren
    :param df: Dataframe
    :return: Bedingung
    """
    bedingung = (df['EF16'] == '2')
    return bedingung


def schuldenbereinigungsplan(df):
    """
    Bedingung zur Ermittlung der Verfahren mit angenommenen Schuldenbereinigungsplan
    :param df: Dataframe
    :return: Bedingung
    """
    bedingung = (df['EF16'] == '3')
    return bedingung
