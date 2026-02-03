# -*- coding: utf-8 -*-

import os
import csv
import time
import datetime
import traceback

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.common import exceptions

from Scripte import Config


def cfg_file(land: str) -> str:
    p = os.path.join("Bekanntmachungen", f"config_{land}.ini")
    if os.path.exists(p):
        return p
    return f"config_{land}.ini"


def read_timeouts(config):
    def _get(sec, key, default):
        try:
            return int(config.get(sec, {}).get(key, default))
        except Exception:
            return int(default)

    wait_short = _get("timeouts", "wait_short", 30)
    wait_long = _get("timeouts", "wait_long", 120)
    page_load = _get("timeouts", "page_load", wait_long)
    return wait_short, wait_long, page_load


def ensure_csv_exists(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Datum", "Aktenzeichen", "Gericht", "Schuldner", "Sitz", "Register", "VeroeffText"])


def log_line(msg):
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("protokoll.txt", "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def log_exc(prefix, e):
    log_line(f"{prefix}: {repr(e)}")
    log_line(traceback.format_exc())


class Auslesen:
    def __init__(self, ausgabe):
        self.ausgabe = ausgabe

        self.bundesland = [("Bayern", "1")]
        self.driver = None

        self.land = self.bundesland[0][0]
        self.kennung = self.bundesland[0][1]

        self.datum_von = self._datum_von()

        self.ausgabe.txt_edit.append(f"Auslesen wird begonnen: {datetime.datetime.now()}")

        for land, kennung in self.bundesland:
            self.land = land
            self.kennung = kennung
            self.csv_ausl = os.path.join("Bekanntmachungen", f"{self.land}_data.csv")
            self.starten()

        self.ausgabe.txt_edit.append(f"Auslesen abgeschlossen: {datetime.datetime.now()}")

    def _datum_von(self):
        cfg = Config.daten_auslesen(cfg_file(self.land))
        return datetime.datetime.strptime(cfg["insobm"]["datum"], "%d.%m.%Y")

    def _open_search_page_and_set_land(self, url, wait_long):
        # Seite neu laden + Land setzen (wenn Seite in falschem Zustand ist)
        self.driver.get(url)
        wait = WebDriverWait(self.driver, wait_long)
        land_opt = wait.until(ec.element_to_be_clickable((
            By.XPATH,
            f"//select[@name='frm_suche:lsom_bundesland:lsom']/option[@value='{self.kennung}']"
        )))
        land_opt.click()
        return wait

    def _set_datum(self, datum, wait):
        d = datum.strftime("%Y-%m-%d")
        von = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumVon:datumHtml5")))
        von.clear()
        von.send_keys(d)

        bis = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumBis:datumHtml5")))
        bis.clear()
        bis.send_keys(d)

    def starten(self):
        log_line("=== START AUSLESEN ===")
        log_line(f"CWD={os.getcwd()}")
        log_line(f"CSV={self.csv_ausl}")

        url = "https://neu.insolvenzbekanntmachungen.de/ap/suche.jsf"

        try:
            cfg = Config.daten_auslesen(cfg_file(self.land))
            wait_short, wait_long, page_load = read_timeouts(cfg)

            self.ausgabe.txt_edit.append(f"Timeouts: short={wait_short}s long={wait_long}s page_load={page_load}s")

            ensure_csv_exists(self.csv_ausl)

            options = Options()
            options.binary_location = cfg["firefox"]["pfad"]
            options.add_argument("-headless")
            options.set_preference("permissions.default.image", 2)

            self.driver = webdriver.Firefox(options=options)
            self.driver.set_page_load_timeout(page_load)

            wait = self._open_search_page_and_set_land(url, wait_long)

            datum_bis = datetime.datetime.today() - datetime.timedelta(days=1)
            tage = (datum_bis - self.datum_von).days + 1

            for _ in range(tage):
                tag = self.datum_von.strftime("%d.%m.%Y")
                self.ausgabe.txt_edit.append(f"{tag}: Suche läuft …")
                log_line(f"{tag}: Tagstart")

                # Robust: wenn Datumsfelder fehlen -> Seite neu laden und nochmal versuchen
                tries = 0
                while True:
                    tries += 1
                    try:
                        self._set_datum(self.datum_von, wait)
                        break
                    except exceptions.TimeoutException:
                        log_line(f"{tag}: _set_datum timeout (try {tries}) -> reload search page")
                        if tries >= 3:
                            raise
                        wait = self._open_search_page_and_set_land(url, wait_long)

                suchen = wait.until(ec.element_to_be_clickable((By.ID, "frm_suche:cbt_suchen")))
                self.driver.execute_script("arguments[0].click();", suchen)

                def ready(d):
                    if d.find_elements(By.ID, "tbl_ergebnis"):
                        return True
                    src = d.page_source.lower()
                    return ("keine bekanntmachungen" in src or "keine treffer" in src or "keine ergebnisse" in src)

                try:
                    wait.until(ready)
                except exceptions.TimeoutException:
                    log_line(f"{tag}: Timeout nach Suchen -> refresh und retry gleicher Tag")
                    self.driver.refresh()
                    wait = WebDriverWait(self.driver, wait_long)
                    continue

                tables = self.driver.find_elements(By.ID, "tbl_ergebnis")
                if not tables:
                    self.ausgabe.txt_edit.append(f"{tag}: keine Bekanntmachungen")
                    log_line(f"{tag}: keine Bekanntmachungen")
                    self.datum_von += datetime.timedelta(days=1)
                    Config.schreiben(cfg_file(self.land), cfg, "insobm", "datum", self.datum_von.strftime("%d.%m.%Y"))
                    continue

                table = tables[0]
                rows = table.find_elements(By.TAG_NAME, "tr")[1:]
                log_line(f"{tag}: Treffer={len(rows)}")

                row_count = 0

                with open(self.csv_ausl, "a", newline="", encoding="utf-8") as f:
                    w = csv.writer(f, delimiter=";")

                    for i in range(len(rows)):
                        # Aus Tabelle holen
                        datum_txt = self.driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_datum").text
                        az = self.driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_azAkt").text
                        gericht = self.driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_Gericht").text
                        schuldner = self.driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_schuldner").text
                        sitz = self.driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_Sitz").text
                        register = self.driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_register").text

                        # Veröffentlichungstext per Popup öffnen (robust)
                        window_main = self.driver.window_handles[0]

                        btn = wait.until(ec.element_to_be_clickable((
                            By.XPATH,
                            f"(//input[contains(@id, 'frm_detail:j_idt') and @type='image' and @alt='Veröffentlichungstext anzeigen'])[{i+1}]"
                        )))
                        self.driver.execute_script("arguments[0].click();", btn)

                        try:
                            WebDriverWait(self.driver, wait_long).until(lambda d: len(d.window_handles) > 1)
                            window_popup = self.driver.window_handles[1]
                            self.driver.switch_to.window(window_popup)

                            pre = WebDriverWait(self.driver, wait_long).until(
                                ec.presence_of_element_located((By.XPATH, ".//pre[@id='veroefftext']"))
                            )
                            veroeff = pre.text.replace("\n", " ").replace(";", ",")
                        except Exception as e:
                            log_line(f"{tag}: Warnung VeröffText nicht gelesen: {repr(e)}")
                            veroeff = ""
                        finally:
                            # Popup schließen, zurück
                            try:
                                if len(self.driver.window_handles) > 1:
                                    self.driver.close()
                            except Exception:
                                pass
                            try:
                                self.driver.switch_to.window(window_main)
                            except Exception:
                                pass

                        # CSV schreiben (alle 7 Spalten)
                        w.writerow([
                            datum_txt.replace(";", ","),
                            az.replace(";", ","),
                            gericht.replace(";", ","),
                            schuldner.replace(";", ","),
                            sitz.replace(";", ","),
                            register.replace(";", ","),
                            veroeff
                        ])
                        row_count += 1

                        # UI Status (nicht zu viel)
                        if row_count <= 25 or row_count % 100 == 0:
                            self.ausgabe.txt_edit.append(f"{tag}: {az} – {schuldner}")

                        # Crash-sicher flushen
                        if row_count % 20 == 0:
                            f.flush()
                            try:
                                os.fsync(f.fileno())
                            except Exception:
                                pass

                        # kleine Bremse
                        if row_count % 50 == 0:
                            time.sleep(0.2)

                    # am Ende flush
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass

                self.ausgabe.txt_edit.append(f"{tag}: CSV geschrieben ({row_count} Zeilen)")
                log_line(f"{tag}: CSV geschrieben ({row_count} Zeilen)")

                # Zurück zur Suchseite (Zurück-Button wenn vorhanden, sonst reload)
                try:
                    back_btn = wait.until(ec.element_to_be_clickable((By.XPATH, ".//input[@value='Zurück']")))
                    back_btn.click()
                except Exception:
                    wait = self._open_search_page_and_set_land(url, wait_long)

                # Datum vorwärts + INI aktualisieren
                self.datum_von += datetime.timedelta(days=1)
                Config.schreiben(cfg_file(self.land), cfg, "insobm", "datum", self.datum_von.strftime("%d.%m.%Y"))

        except Exception as e:
            log_exc("FATAL", e)
            try:
                self.ausgabe.txt_edit.append(f"FEHLER – Details siehe protokoll.txt: {e}")
            except Exception:
                pass

        finally:
            try:
                if self.driver:
                    self.driver.quit()
            except Exception:
                pass
            log_line("=== ENDE AUSLESEN ===")
