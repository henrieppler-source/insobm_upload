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
        # utf-8-sig => Excel liest Umlaute korrekt beim Doppelklick
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
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

        # aktuell nur Bayern
        self.bundesland = [("Bayern", "1")]

        self.land = self.bundesland[0][0]
        self.kennung = self.bundesland[0][1]

        self.datum_von = self._datum_von()

        self.ausgabe.append(f"Auslesen wird begonnen: {datetime.datetime.now()}")

        for land, kennung in self.bundesland:
            self.land = land
            self.kennung = kennung
            self.csv_ausl = os.path.join("Bekanntmachungen", f"{self.land}_data.csv")

            ensure_csv_exists(self.csv_ausl)
            self.starten_alle_tage()

        self.ausgabe.append(f"Auslesen abgeschlossen: {datetime.datetime.now()}")

    def _datum_von(self):
        cfg = Config.daten_auslesen(cfg_file(self.land))
        return datetime.datetime.strptime(cfg["insobm"]["datum"], "%d.%m.%Y")

    def _make_driver(self, firefox_path: str, page_load: int):
        options = Options()
        options.binary_location = firefox_path

        # --- Headless aus INI lesen (robust) ---
        cfg = Config.daten_auslesen(cfg_file(self.land))
        headless_raw = str(cfg.get("selenium", {}).get("headless", "1")).strip().lower()
        headless = headless_raw in ("1", "true", "yes", "on")

        if headless:
            options.add_argument("-headless")

        # Ressourcen sparen
        options.set_preference("permissions.default.image", 2)

        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(page_load)
        return driver

    def _open_search_and_set_land(self, driver, url, wait_long):
        driver.get(url)
        wait = WebDriverWait(driver, wait_long)
        land_opt = wait.until(ec.element_to_be_clickable((
            By.XPATH,
            f"//select[@name='frm_suche:lsom_bundesland:lsom']/option[@value='{self.kennung}']"
        )))
        land_opt.click()
        return wait

    def _set_datum(self, driver, wait, datum):
        d = datum.strftime("%Y-%m-%d")
        von = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumVon:datumHtml5")))
        von.clear()
        von.send_keys(d)

        bis = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumBis:datumHtml5")))
        bis.clear()
        bis.send_keys(d)

    def starten_alle_tage(self):
        log_line("=== START AUSLESEN ===")
        log_line(f"CWD={os.getcwd()}")
        log_line(f"CSV={self.csv_ausl}")

        url = "https://neu.insolvenzbekanntmachungen.de/ap/suche.jsf"

        cfg = Config.daten_auslesen(cfg_file(self.land))
        wait_short, wait_long, page_load = read_timeouts(cfg)

        # !!! GUI-thread-sicher:
        self.ausgabe.append(f"Timeouts: short={wait_short}s long={wait_long}s page_load={page_load}s")

        datum_bis = datetime.datetime.today() - datetime.timedelta(days=1)
        tage = (datum_bis - self.datum_von).days + 1

        for _ in range(tage):
            tag = self.datum_von.strftime("%d.%m.%Y")
            self.ausgabe.append(f"{tag}: starte Tag (neue Browser-Session)")
            log_line(f"{tag}: Tagstart")

            driver = None
            try:
                driver = self._make_driver(cfg["firefox"]["pfad"], page_load)
                wait = self._open_search_and_set_land(driver, url, wait_long)

                # Datum setzen (mit Retry + Reload)
                tries = 0
                while True:
                    tries += 1
                    try:
                        self._set_datum(driver, wait, self.datum_von)
                        break
                    except exceptions.TimeoutException:
                        log_line(f"{tag}: _set_datum timeout (try {tries}) -> reload")
                        if tries >= 3:
                            raise
                        wait = self._open_search_and_set_land(driver, url, wait_long)

                suchen = wait.until(ec.element_to_be_clickable((By.ID, "frm_suche:cbt_suchen")))
                driver.execute_script("arguments[0].click();", suchen)

                def ready(d):
                    if d.find_elements(By.ID, "tbl_ergebnis"):
                        return True
                    src = d.page_source.lower()
                    return ("keine bekanntmachungen" in src or "keine treffer" in src or "keine ergebnisse" in src)

                wait.until(ready)

                tables = driver.find_elements(By.ID, "tbl_ergebnis")
                if not tables:
                    self.ausgabe.append(f"{tag}: keine Bekanntmachungen")
                    log_line(f"{tag}: keine Bekanntmachungen")
                    self.datum_von += datetime.timedelta(days=1)
                    # !!! NICHT cfg (dict) übergeben:
                    Config.schreiben(cfg_file(self.land), None, "insobm", "datum", self.datum_von.strftime("%d.%m.%Y"))
                    continue

                table = tables[0]
                rows = table.find_elements(By.TAG_NAME, "tr")[1:]
                log_line(f"{tag}: Treffer={len(rows)}")

                row_count = 0

                with open(self.csv_ausl, "a", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f, delimiter=";")

                    for i in range(len(rows)):
                        datum_txt = driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_datum").text
                        az = driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_azAkt").text
                        gericht = driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_Gericht").text
                        schuldner = driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_schuldner").text
                        sitz = driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_Sitz").text
                        register = driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i}\\:otx_register").text

                        veroeff = ""
                        try:
                            window_main = driver.window_handles[0]
                            btn = wait.until(ec.element_to_be_clickable((
                                By.XPATH,
                                f"(//input[contains(@id, 'frm_detail:j_idt') and @type='image' and @alt='Veröffentlichungstext anzeigen'])[{i+1}]"
                            )))
                            driver.execute_script("arguments[0].click();", btn)

                            WebDriverWait(driver, wait_long).until(lambda d: len(d.window_handles) > 1)
                            window_popup = driver.window_handles[1]
                            driver.switch_to.window(window_popup)

                            pre = WebDriverWait(driver, wait_long).until(
                                ec.presence_of_element_located((By.XPATH, ".//pre[@id='veroefftext']"))
                            )
                            veroeff = pre.text.replace("\n", " ").replace(";", ",")
                        except Exception as e:
                            log_line(f"{tag}: Warnung VeröffText nicht gelesen: {repr(e)}")
                            veroeff = ""
                        finally:
                            try:
                                if len(driver.window_handles) > 1:
                                    driver.close()
                            except Exception:
                                pass
                            try:
                                driver.switch_to.window(window_main)
                            except Exception:
                                pass

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

                        if row_count <= 20 or row_count % 100 == 0:
                            self.ausgabe.append(f"{tag}: {row_count}/{len(rows)} …")

                        if row_count % 20 == 0:
                            f.flush()
                            try:
                                os.fsync(f.fileno())
                            except Exception:
                                pass

                        if row_count % 50 == 0:
                            time.sleep(0.2)

                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass

                self.ausgabe.append(f"{tag}: CSV geschrieben ({row_count} Zeilen)")
                log_line(f"{tag}: CSV geschrieben ({row_count} Zeilen)")

                self.datum_von += datetime.timedelta(days=1)
                # !!! NICHT cfg (dict) übergeben:
                Config.schreiben(cfg_file(self.land), None, "insobm", "datum", self.datum_von.strftime("%d.%m.%Y"))

            except Exception as e:
                log_exc(f"FATAL am Tag {tag}", e)
                try:
                    self.ausgabe.append(f"{tag}: FEHLER – Details siehe protokoll.txt")
                except Exception:
                    pass
                break

            finally:
                try:
                    if driver:
                        driver.quit()
                except Exception:
                    pass

        log_line("=== ENDE AUSLESEN ===")
