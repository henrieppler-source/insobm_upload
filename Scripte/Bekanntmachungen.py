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


# =========================================================
# Config / Logging Helper
# =========================================================

def cfg_file(land: str) -> str:
    p = os.path.join("Bekanntmachungen", f"config_{land}.ini")
    if os.path.exists(p):
        return p
    return f"config_{land}.ini"


def cfg_get(cfg, section: str, option: str, fallback: str = "") -> str:
    """
    Robust: funktioniert sowohl für dict (cfg[section][option])
    als auch für configparser.ConfigParser (cfg.get(section, option)).
    """
    if isinstance(cfg, dict):
        try:
            return str(cfg.get(section, {}).get(option, fallback))
        except Exception:
            return str(fallback)

    try:
        return str(cfg.get(section, option, fallback=fallback))
    except TypeError:
        try:
            if cfg.has_option(section, option):
                return str(cfg.get(section, option))
        except Exception:
            pass
        return str(fallback)
    except Exception:
        return str(fallback)


def read_timeouts(cfg):
    def _get_int(section, option, default):
        try:
            return int(cfg_get(cfg, section, option, str(default)))
        except Exception:
            return int(default)

    wait_short = _get_int("timeouts", "wait_short", 30)
    wait_long  = _get_int("timeouts", "wait_long", 180)
    page_load  = _get_int("timeouts", "page_load", wait_long)
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


# =========================================================
# Hauptklasse
# =========================================================

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

    # -----------------------------------------------------

    def _datum_von(self):
        cfg = Config.daten_auslesen(cfg_file(self.land))
        return datetime.datetime.strptime(cfg_get(cfg, "insobm", "datum", "01.01.2000"), "%d.%m.%Y")

    # -----------------------------------------------------

    def _make_driver(self, firefox_path: str, page_load: int, headless: bool):
        options = Options()
        options.binary_location = firefox_path

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

    def _set_datum(self, wait, datum):
        d = datum.strftime("%Y-%m-%d")

        von = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumVon:datumHtml5")))
        von.clear()
        von.send_keys(d)

        bis = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumBis:datumHtml5")))
        bis.clear()
        bis.send_keys(d)

    # -----------------------------------------------------

    def starten_alle_tage(self):
        log_line("=== START AUSLESEN ===")
        log_line(f"CWD={os.getcwd()}")
        log_line(f"CSV={self.csv_ausl}")

        url = "https://neu.insolvenzbekanntmachungen.de/ap/suche.jsf"

        cfg = Config.daten_auslesen(cfg_file(self.land))
        wait_short, wait_long, page_load = read_timeouts(cfg)

        firefox_path = cfg_get(cfg, "firefox", "pfad", "")
        headless_raw = cfg_get(cfg, "selenium", "headless", "1").strip().lower()
        headless = headless_raw in ("1", "true", "yes", "on")

        self.ausgabe.append(
            f"Timeouts: short={wait_short}s long={wait_long}s page_load={page_load}s | headless={1 if headless else 0}"
        )

        datum_bis = datetime.datetime.today() - datetime.timedelta(days=1)
        tage = (datum_bis - self.datum_von).days + 1

        for _ in range(tage):
            tag = self.datum_von.strftime("%d.%m.%Y")
            self.ausgabe.append(f"{tag}: starte Tag (neue Browser-Session)")
            log_line(f"{tag}: Tagstart")

            driver = None
            tag_ok = True  # <<< Tages-Abbruch-Fix: nur bei True Datum fortschreiben

            try:
                driver = self._make_driver(firefox_path, page_load, headless)
                wait = self._open_search_and_set_land(driver, url, wait_long)

                # Datum setzen (mit Retry + Reload)
                tries = 0
                while True:
                    tries += 1
                    try:
                        self._set_datum(wait, self.datum_von)
                        break
                    except exceptions.TimeoutException:
                        log_line(f"{tag}: _set_datum timeout (try {tries}) -> reload")
                        if tries >= 3:
                            tag_ok = False
                            raise
                        wait = self._open_search_and_set_land(driver, url, wait_long)

                # Suchen klicken
                suchen = wait.until(ec.element_to_be_clickable((By.ID, "frm_suche:cbt_suchen")))
                driver.execute_script("arguments[0].click();", suchen)

                # warten bis Ergebnis oder "keine Treffer"
                def ready(d):
                    if d.find_elements(By.ID, "tbl_ergebnis"):
                        return True
                    src = d.page_source.lower()
                    return ("keine bekanntmachungen" in src or "keine treffer" in src or "keine ergebnisse" in src)

                try:
                    wait.until(ready)
                except exceptions.TimeoutException:
                    tag_ok = False
                    raise

                tables = driver.find_elements(By.ID, "tbl_ergebnis")
                if not tables:
                    self.ausgabe.append(f"{tag}: keine Bekanntmachungen")
                    log_line(f"{tag}: keine Bekanntmachungen")
                else:
                    table = tables[0]
                    rows = table.find_elements(By.TAG_NAME, "tr")[1:]
                    log_line(f"{tag}: Treffer={len(rows)}")

                    row_count = 0

                    with open(self.csv_ausl, "a", newline="", encoding="utf-8-sig") as f:
                        w = csv.writer(f, delimiter=";")

                        for i in range(len(rows)):
                            # Falls DOM neu -> rows neu holen
                            try:
                                row = rows[i]
                            except Exception:
                                table = driver.find_element(By.ID, "tbl_ergebnis")
                                rows = table.find_elements(By.TAG_NAME, "tr")[1:]
                                row = rows[i]

                            try:
                                datum_txt = row.find_element(By.CSS_SELECTOR, "[id$=':otx_datum']").text
                                az        = row.find_element(By.CSS_SELECTOR, "[id$=':otx_azAkt']").text
                                gericht   = row.find_element(By.CSS_SELECTOR, "[id$=':otx_Gericht']").text
                                schuldner = row.find_element(By.CSS_SELECTOR, "[id$=':otx_schuldner']").text
                                sitz      = row.find_element(By.CSS_SELECTOR, "[id$=':otx_Sitz']").text
                                register  = row.find_element(By.CSS_SELECTOR, "[id$=':otx_register']").text
                            except exceptions.StaleElementReferenceException:
                                table = driver.find_element(By.ID, "tbl_ergebnis")
                                rows = table.find_elements(By.TAG_NAME, "tr")[1:]
                                row = rows[i]
                                datum_txt = row.find_element(By.CSS_SELECTOR, "[id$=':otx_datum']").text
                                az        = row.find_element(By.CSS_SELECTOR, "[id$=':otx_azAkt']").text
                                gericht   = row.find_element(By.CSS_SELECTOR, "[id$=':otx_Gericht']").text
                                schuldner = row.find_element(By.CSS_SELECTOR, "[id$=':otx_schuldner']").text
                                sitz      = row.find_element(By.CSS_SELECTOR, "[id$=':otx_Sitz']").text
                                register  = row.find_element(By.CSS_SELECTOR, "[id$=':otx_register']").text

                            veroeff = ""
                            veroeff_ok = True

                            try:
                                btn = row.find_element(By.CSS_SELECTOR, "input[alt='Veröffentlichungstext anzeigen']")
                                driver.execute_script("arguments[0].click();", btn)

                                WebDriverWait(driver, wait_long).until(lambda d: len(d.window_handles) > 1)
                                driver.switch_to.window(driver.window_handles[1])

                                pre = WebDriverWait(driver, wait_long).until(
                                    ec.presence_of_element_located((By.XPATH, ".//pre[@id='veroefftext']"))
                                )
                                veroeff = pre.text.replace("\n", " ").replace(";", ",")
                            except exceptions.TimeoutException:
                                log_line(f"{tag}: Warnung VeröffText nicht gelesen: TimeoutException()")
                                veroeff = ""
                                veroeff_ok = False
                                tag_ok = False  # <<< Tages-Abbruch: bei Selenium-Fehler Tag als "nicht OK"
                            except exceptions.StaleElementReferenceException:
                                log_line(f"{tag}: Warnung VeröffText nicht gelesen: StaleElementReferenceException()")
                                veroeff = ""
                                veroeff_ok = False
                                tag_ok = False
                            except Exception as e:
                                log_line(f"{tag}: Warnung VeröffText nicht gelesen: {repr(e)}")
                                veroeff = ""
                                veroeff_ok = False
                                tag_ok = False
                            finally:
                                # Popup cleanup
                                try:
                                    while len(driver.window_handles) > 1:
                                        driver.switch_to.window(driver.window_handles[-1])
                                        driver.close()
                                    driver.switch_to.window(driver.window_handles[0])
                                except Exception:
                                    pass

                            # <<< Tages-Abbruch-Fix: sobald ein Selenium-Fehler im Tag war -> sauber raus
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

                            if not veroeff_ok:
                                # WICHTIG: NICHT weiter am DOM arbeiten, Tag kontrolliert beenden
                                log_line(f"{tag}: Abbruch Tag nach VeröffText-Fehler (Zeile {i+1})")
                                break

                        # final flush
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except Exception:
                            pass

                    self.ausgabe.append(f"{tag}: CSV geschrieben ({row_count} Zeilen)")
                    log_line(f"{tag}: CSV geschrieben ({row_count} Zeilen)")

            except Exception as e:
                tag_ok = False
                log_exc(f"FATAL am Tag {tag}", e)
                try:
                    self.ausgabe.append(f"{tag}: FEHLER – Details siehe protokoll.txt")
                except Exception:
                    pass

            finally:
                try:
                    if driver:
                        driver.quit()
                except Exception:
                    pass

            # <<< Tages-Abbruch-Fix: Datum & INI nur fortschreiben, wenn der Tag wirklich OK war
            if tag_ok:
                self.datum_von += datetime.timedelta(days=1)
                Config.schreiben(cfg_file(self.land), None, "insobm", "datum", self.datum_von.strftime("%d.%m.%Y"))
                log_line(f"{tag}: Tag OK -> Datum fortgeschrieben auf {self.datum_von.strftime('%d.%m.%Y')}")
            else:
                self.ausgabe.append(f"{tag}: abgebrochen – Datum bleibt unverändert")
                log_line(f"{tag}: Tag NICHT OK -> Datum bleibt {self.datum_von.strftime('%d.%m.%Y')} (kein INI-Write)")
                break  # kontrollierter Abbruch der Gesamtschleife

        log_line("=== ENDE AUSLESEN ===")
