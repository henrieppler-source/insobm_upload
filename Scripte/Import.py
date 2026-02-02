# -*- coding: utf-8 -*-

import pandas as pd


def csv(pfad):
    """
    Eine CSV-Datei in ein Pandas-Dataframe einlesen
    :param pfad: Pfad zur CSV-Datei, die eingelsen werden soll
    :return: Data-Frame
    """
    df_aj = pd.read_csv(pfad, sep=";", index_col=False, dtype=str, names=[
        "EF1", "EF2", "EF3", "EF4", "EF5", "EF6", "EF7", "EF8", "EF9", "EF10", "EF11", "EF12", "EF13", "EF14",
        "EF15", "EF16", "EF17", "EF18", "EF19", "EF19N", "EF20", "EF23", "EF24", "EF25", "EF26", "EF27", "EF28",
        "EF29", "EF30", "EF31", "EF32", "EF33", "EF34", "EF35", "EF36", "EF37", "EF38", "EF39", "EF40", "EF41",
        "EF42", "EF43", "EF44", "EF45", "EF46", "EF47", "EF48", "EF49", "EF49N", "EF50", "EF51", "EF52", "EF53",
        "EF54N1", "EF54N2", "EF54N3", "EF54N4", "EF54N5", "EF54N6", "EF54N7", "EF55", "EF56", "EF56N1", "EF56N2",
        "EF56N3", "EF57", "EF58", "EF59", "EFLAND", "EFSPAET", "EFSPAETX1", "EFSPAETX2", "EFSPAETB", "EFJAHRB",
        "EFJAHRX1", "EFJAHRX2", "BESCHLX1", "BESCHLX2", "RSBZUL", "UMSNR", "MELDARTU1", "MELDARTU2", "MELDARTU3",
        "MELDARTU4", "MELDARTU5", "MELDARTU6", "BEENDOHNE", "EF60", "EF61", "EF62", "EF63", "EF64", "EF65",
        "EF66", "EF67", "EF68", "EF69", "EF70", "EF71", "EF72", "EF73", "EF74", "EF75", "EF76", "EF77"])

    return df_aj
