# -*- coding: utf-8 -*-

import os
import csv
import datetime

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.common import exceptions

from Scripte import Config


def cfg_file(land: str) -> str:
    """
    Bevorzugt: Bekanntmachungen/config_<Land>.ini
    Fallback:  config_<Land>.ini (alte Ablage neben exe)
    """
    p = os.path.join("Bekanntmachungen", f"config_{land}.ini")
    if os.path.exists(p):
        return p
    return f"config_{land}.ini"


def read_timeouts(config) -> tuple[int, int, int]:
    """
    Liest Timeouts aus [timeouts] (Optional). Fallback auf Defaults.
    """
    def _iget(section: str, key: str, default: int) -> int:
        try:
            # config ist ConfigParser; Zugriff wie dict möglich
            return int(config.get(section, {}).get(key, default))
        except Exception:
            return int(default)

    wait_short = _iget("timeouts", "wait_short", 30)
    wait_long = _iget("timeouts", "wait_long", 90)
    page_load = _iget("timeouts", "page_load", wait_long)
    return wait_short, wait_long, page_load


def ensure_csv_exists(path: str):
    """
    Legt die CSV sofort an (Header), damit man während des Laufs schon sieht: da kommt was.
    """
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Datum", "Aktenzeichen", "Gericht", "Schuldner", "Sitz", "Register", "VeroeffText"])


class Auslesen:
    def __init__(self, ausgabe):
        """
        Auslesen der Insolvenzbekanntmachungen.
        :param ausgabe: Textfeld auf dem Fenster (hier Ausgabefenster).
        """
        # Länder, die das Programm nutzen: ("Bremen", "4") | ("Hamburg", "5"),("Schleswig-Holstein", "14")
        # restliche Länder: ("Bayern", "1") | ("Thüringen", "15") | ("Sachsen-Anhalt", "13") | ("Rheinland-Pfalz", "10")
        self.bundesland = [("Bayern", "1")]

        self.land = self.bundesland[0][0]
        self.kennung = self.bundesland[0][1]
        self.driver = None
        self.ausgabe = ausgabe

        # Startdatum aus INI
        self.datum_von = self.__datum_von()

        self.ausgabe.txt_edit.append(f'Auslesen wird begonnen: {datetime.datetime.today()}')

        for bundes_land in self.bundesland:
            self.land = bundes_land[0]
            self.kennung = bundes_land[1]
            self.csv_ausl = os.path.join("Bekanntmachungen", f"{self.land}_data.csv")
            self.starten()

        self.ausgabe.txt_edit.append(f'Auslesen abgeschlossen: {datetime.datetime.today()}')

    def __datum_von(self):
        """
        Ermittlung des ersten Auslesetages aus config_<Land>.ini in Sektion [insobm], Option datum.
        """
        datei = cfg_file(self.land)
        datum_config = datetime.datetime.strptime(
            Config.daten_auslesen(datei)['insobm']['datum'], "%d.%m.%Y"
        )
        return datum_config

    def __schreibe_datum(self, datum, wait_long: int):
        """
        Eintragen der Datumsangaben in die Eingabefelder
        """
        wait = WebDriverWait(self.driver, wait_long)
        auslesedatum = datetime.datetime.strftime(datum, "%Y-%m-%d")

        datum_von = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumVon:datumHtml5")))
        datum_von.clear()
        datum_von.send_keys(auslesedatum)

        datum_bis = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumBis:datumHtml5")))
        datum_bis.clear()
        datum_bis.send_keys(auslesedatum)

    def starten(self):
        """
        Hier werden die Bekanntmachungen auf der neuen Seite der Insolvenzbekanntmachungen ausgelesen.
        Robuste Version:
        - Timeouts per INI
        - Timeout != "keine Bekanntmachungen"
        - Statusmeldungen pro Tag
        """
        self.ausgabe.txt_edit.append("     Auslesen der neuen Verfahren wird gestartet.")

        # URL (Session-Teil weglassen, sonst ist es fragil)
        url = "https://neu.insolvenzbekanntmachungen.de/ap/suche.jsf"

        # Enddatum bestimmen
        datum_bis = datetime.datetime.today() - datetime.timedelta(days=1)
        anz_tage = (datum_bis - self.datum_von + datetime.timedelta(days=1)).days

        if anz_tage < 1:
            self.ausgabe.txt_edit.append("     Es wurden bereits Daten ausgelesen.")
            return

        self.ausgabe.txt_edit.append(
            f"     Auslesen wird gestartet.\n     Für {anz_tage} Tag(e) werden die Bekanntmachungen ausgelesen"
        )

        # CSV anlegen (so sieht man sofort, dass er schreibt)
        ensure_csv_exists(self.csv_ausl)

        # Browser initialisieren
        options = Options()
        config = Config.daten_auslesen(cfg_file(self.land))
        wait_short, wait_long, page_load = read_timeouts(config)

        # Status
        self.ausgabe.txt_edit.append(
            f"     Timeouts: wait_short={wait_short}s, wait_long={wait_long}s, page_load={page_load}s"
        )

        options.binary_location = r"{0}".format(config["firefox"]["pfad"])

        # Headless möglich (unsichtbar, schneller) – du wolltest das
        options.add_argument("-headless")

        # Ressourcen sparen (optional, bringt oft was)
        options.set_preference("permissions.default.image", 2)  # Bilder aus

        self.driver = webdriver.Firefox(options=options)
        self.driver.set_page_load_timeout(page_load)
        self.driver.get(url)

        wait = WebDriverWait(self.driver, wait_long)

        # Bundesland einstellen
        option_land = wait.until(ec.element_to_be_clickable((
            By.XPATH,
            f"//select[@name='frm_suche:lsom_bundesland:lsom']/option[@value='{self.kennung}']"
        )))
        option_land.click()

        # Arrays
        arr_temp_werte = []
        arr_werte = []

        # Für jeden Tag seit datum_von auslesen
        for _ in range(anz_tage):
            # Status pro Tag
            self.ausgabe.txt_edit.append(f"     {self.datum_von.strftime('%d.%m.%Y')}: Suche läuft ...")

            # Datum in die Felder eintragen
            self.__schreibe_datum(self.datum_von, wait_long)

            # Suchen klicken
            try:
                suchen_klick = wait.until(ec.element_to_be_clickable((By.ID, "frm_suche:cbt_suchen")))
                self.driver.execute_script("arguments[0].click();", suchen_klick)
            except Exception as e:
                self.ausgabe.txt_edit.append(f"     Fehler beim Klicken auf Suchen: {e}")
                # nächsten Tag versuchen
                self.datum_von += datetime.timedelta(days=1)
                continue

            # Robust warten: entweder Ergebnis-Tabelle oder eindeutige "keine Treffer" Situation
            def results_ready(d):
                if d.find_elements(By.ID, "tbl_ergebnis"):
                    return True
                src = d.page_source.lower()
                if ("keine bekanntmachungen" in src) or ("keine treffer" in src) or ("keine ergebnisse" in src):
                    return True
                return False

            try:
                wait.until(results_ready)
            except exceptions.TimeoutException:
                # Nicht als "keine Bekanntmachungen" werten – Seite war zu langsam
                self.ausgabe.txt_edit.append(
                    f"     {self.datum_von.strftime('%d.%m.%Y')}: Seite langsam (Timeout). Neuer Versuch ..."
                )
                try:
                    self.driver.refresh()
                except Exception:
                    pass
                # NICHT Datum erhöhen, Tag nochmal versuchen
                continue

            tables = self.driver.find_elements(By.ID, "tbl_ergebnis")
            if not tables:
                # wirklich keine Treffer
                self.ausgabe.txt_edit.append(
                    f"     {self.datum_von.strftime('%d.%m.%Y')}: Heute keine Bekanntmachungen"
                )
                # Datum hochzählen + INI aktualisieren
                self.datum_von += datetime.timedelta(days=1)
                Config.schreiben(
                    datei=cfg_file(self.land),
                    config=config,
                    sektion="insobm",
                    option="datum",
                    wert=self.datum_von.strftime("%d.%m.%Y"),
                )
                continue

            table = tables[0]

            # Treffer-Zeilen
            rows = table.find_elements(By.TAG_NAME, "tr")
            if len(rows) <= 1:
                # Tabelle da, aber leer (ungewöhnlich)
                self.ausgabe.txt_edit.append(
                    f"     {self.datum_von.strftime('%d.%m.%Y')}: Ergebnis-Tabelle leer"
                )
                self.datum_von += datetime.timedelta(days=1)
                Config.schreiben(datei=cfg_file(self.land), config=config, sektion="insobm",
                                 option="datum", wert=self.datum_von.strftime("%d.%m.%Y"))
                continue

            anz_bekannt = 0

            for i in range(1, len(rows)):
                # Tabellenwerte auslesen
                datum_neu = self.driver.find_element(
                    By.CSS_SELECTOR, f"[id='tbl_ergebnis\\:{i - 1}\\:otx_datum']"
                ).text
                arr_temp_werte.append(datum_neu)

                aktenzeichen_neu = self.driver.find_element(
                    By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i - 1}\\:otx_azAkt"
                ).text
                arr_temp_werte.append(aktenzeichen_neu)

                gericht_neu = self.driver.find_element(
                    By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i - 1}\\:otx_Gericht"
                ).text
                arr_temp_werte.append(gericht_neu.replace(",", ";"))

                schuldner_neu = self.driver.find_element(
                    By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i - 1}\\:otx_schuldner"
                ).text
                arr_temp_werte.append(schuldner_neu.replace(",", ";"))

                sitz_neu = self.driver.find_element(
                    By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i - 1}\\:otx_Sitz"
                ).text
                arr_temp_werte.append(sitz_neu.replace(",", ";"))

                register_neu = self.driver.find_element(
                    By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i - 1}\\:otx_register"
                ).text
                arr_temp_werte.append(register_neu.replace(",", ";"))

                # Veröffentlichungstext (wie bisher via Popup)
                window_now = self.driver.window_handles[0]
                text_anzeige = wait.until(ec.element_to_be_clickable((
                    By.XPATH,
                    f"(//input[contains(@id, 'frm_detail:j_idt') and @type='image' and "
                    f"@alt='Veröffentlichungstext anzeigen'])[{i}]"
                )))
                self.driver.execute_script("arguments[0].click();", text_anzeige)

                # warten bis zweites Fenster da ist
                try:
                    WebDriverWait(self.driver, wait_long).until(lambda d: len(d.window_handles) > 1)
                except exceptions.TimeoutException:
                    self.ausgabe.txt_edit.append("     Warnung: Veröffentlichungstext-Fenster kam nicht.")
                    arr_temp_werte.append("")
                    arr_werte.append(arr_temp_werte)
                    arr_temp_werte = []
                    continue

                window_after = self.driver.window_handles[1]
                self.driver.switch_to.window(window_after)

                veroefftext = wait.until(ec.presence_of_element_located((By.XPATH, ".//pre[@id='veroefftext']"))).text
                veroeff_text = "{0}".format(veroefftext).replace("\n", " ").replace(",", ";")
                arr_temp_werte.append(veroeff_text)

                arr_werte.append(arr_temp_werte)
                self.driver.close()
                self.driver.switch_to.window(window_now)

                self.ausgabe.txt_edit.append(
                    f"     {arr_temp_werte[0]}  -  {arr_temp_werte[1]}  -  {arr_temp_werte[3]}"
                )
                arr_temp_werte = []
                anz_bekannt += 1

            # Zurück zur Trefferliste / Suchseite
            try:
                zurueck = wait.until(ec.element_to_be_clickable((By.XPATH, ".//input[@value='Zurück']")))
                zurueck.click()
            except Exception:
                # notfalls back
                try:
                    self.driver.back()
                except Exception:
                    pass

            # CSV schreiben (pro Tag, damit man sofort was sieht)
            with open(self.csv_ausl, "a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file, delimiter=",")
                for r in arr_werte:
                    writer.writerow(r)

            arr_werte = []

            self.ausgabe.txt_edit.append(f"     CSV geschrieben. Anzahl Treffer: {anz_bekannt}")

            # Datum hoch zählen + INI aktualisieren
            self.datum_von += datetime.timedelta(days=1)
            Config.schreiben(
                datei=cfg_file(self.land),
                config=config,
                sektion="insobm",
                option="datum",
                wert=self.datum_von.strftime("%d.%m.%Y"),
            )

        # Browser schließen
        try:
            self.driver.quit()
        except Exception:
            pass
