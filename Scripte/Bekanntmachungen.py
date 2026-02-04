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
    if isinstance(cfg, dict):
        try:
            return str(cfg.get(section, {}).get(option, fallback))
        except Exception:
            return str(fallback)

    try:
        return str(cfg.get(section, option, fallback=fallback))
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
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([
                "Datum", "Aktenzeichen", "Gericht",
                "Schuldner", "Sitz", "Register", "VeroeffText"
            ])


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
        return datetime.datetime.strptime(
            cfg_get(cfg, "insobm", "datum", "01.01.2000"),
            "%d.%m.%Y"
        )

    # -----------------------------------------------------

    def _make_driver(self, firefox_path: str, page_load: int, headless: bool):
        options = Options()
        options.binary_location = firefox_path

        if headless:
            options.add_argument("-headless")

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

            von = wait.until(ec.presence_of_element_located(
                (By.ID, "frm_suche:ldi_datumVon:datumHtml5")
            ))
            bis = wait.until(ec.presence_of_element_located(
                (By.ID, "frm_suche:ldi_datumBis:datumHtml5")
            ))

            # JSF-sicher setzen per JavaScript
            driver.execute_script("""
                arguments[0].scrollIntoView({block: 'center'});
                arguments[0].value = arguments[2];
                arguments[0].dispatchEvent(new Event('change'));
                arguments[1].scrollIntoView({block: 'center'});
                arguments[1].value = arguments[2];
                arguments[1].dispatchEvent(new Event('change'));
            """, von, bis, d)

    # -----------------------------------------------------

    def starten_alle_tage(self):
        log_line("=== START AUSLESEN ===")

        url = "https://neu.insolvenzbekanntmachungen.de/ap/suche.jsf"

        cfg = Config.daten_auslesen(cfg_file(self.land))
        wait_short, wait_long, page_load = read_timeouts(cfg)

        firefox_path = cfg_get(cfg, "firefox", "pfad", "")
        headless = cfg_get(cfg, "selenium", "headless", "1").lower() in ("1", "true", "yes")

        self.ausgabe.append(
            f"Timeouts: short={wait_short}s long={wait_long}s page_load={page_load}s | headless={int(headless)}"
        )

        datum_bis = datetime.datetime.today() - datetime.timedelta(days=1)
        tage = (datum_bis - self.datum_von).days + 1

        for _ in range(tage):
            tag = self.datum_von.strftime("%d.%m.%Y")
            self.ausgabe.append(f"{tag}: starte Tag")
            log_line(f"{tag}: Tagstart")

            driver = None
            tag_ok = True
            veroeff_fail_count = 0   # <<< STUFE-2-ZÄHLER

            try:
                driver = self._make_driver(firefox_path, page_load, headless)
                wait = self._open_search_and_set_land(driver, url, wait_long)

                self._set_datum(driver, wait, self.datum_von)


                suchen = wait.until(ec.element_to_be_clickable((By.ID, "frm_suche:cbt_suchen")))
                driver.execute_script("arguments[0].click();", suchen)

                wait.until(lambda d: d.find_elements(By.ID, "tbl_ergebnis"))

                table = driver.find_element(By.ID, "tbl_ergebnis")
                rows = table.find_elements(By.TAG_NAME, "tr")[1:]
                log_line(f"{tag}: Treffer={len(rows)}")

                with open(self.csv_ausl, "a", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f, delimiter=";")

                    for i in range(len(rows)):
                        row = rows[i]

                        datum_txt = row.find_element(By.CSS_SELECTOR, "[id$=':otx_datum']").text
                        az        = row.find_element(By.CSS_SELECTOR, "[id$=':otx_azAkt']").text
                        gericht   = row.find_element(By.CSS_SELECTOR, "[id$=':otx_Gericht']").text
                        schuldner = row.find_element(By.CSS_SELECTOR, "[id$=':otx_schuldner']").text
                        sitz      = row.find_element(By.CSS_SELECTOR, "[id$=':otx_Sitz']").text
                        register  = row.find_element(By.CSS_SELECTOR, "[id$=':otx_register']").text

                        veroeff = ""
                        try:
                            btn = row.find_element(By.CSS_SELECTOR, "input[alt='Veröffentlichungstext anzeigen']")
                            driver.execute_script("arguments[0].click();", btn)

                            WebDriverWait(driver, wait_long).until(lambda d: len(d.window_handles) > 1)
                            driver.switch_to.window(driver.window_handles[1])

                            pre = WebDriverWait(driver, wait_long).until(
                                ec.presence_of_element_located((By.ID, "veroefftext"))
                            )
                            veroeff = pre.text.replace("\n", " ").replace(";", ",")
                            veroeff_fail_count = 0   # <<< Erfolg → Reset
                        except Exception:
                            veroeff = ""
                            veroeff_fail_count += 1
                            log_line(f"{tag}: VeröffText fehlgeschlagen ({veroeff_fail_count})")
                        finally:
                            try:
                                while len(driver.window_handles) > 1:
                                    driver.switch_to.window(driver.window_handles[-1])
                                    driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                            except Exception:
                                pass

                        w.writerow([
                            datum_txt, az, gericht,
                            schuldner, sitz, register, veroeff
                        ])

                        if veroeff_fail_count >= 10:
                            log_line(f"{tag}: 10 VeröffText-Fehler in Folge → Tagesabbruch")
                            tag_ok = False
                            break

                        if i % 100 == 0:
                            self.ausgabe.append(f"{tag}: {i+1}/{len(rows)}")

            except Exception as e:
                tag_ok = False
                log_exc(f"FATAL am Tag {tag}", e)

            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

            if tag_ok:
                self.datum_von += datetime.timedelta(days=1)
                Config.schreiben(
                    cfg_file(self.land),
                    None,
                    "insobm",
                    "datum",
                    self.datum_von.strftime("%d.%m.%Y")
                )
                log_line(f"{tag}: Tag OK")
            else:
                self.ausgabe.append(f"{tag}: abgebrochen – Datum bleibt")
                log_line(f"{tag}: Tag abgebrochen")
                break

        log_line("=== ENDE AUSLESEN ===")

