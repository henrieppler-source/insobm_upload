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
# Helpers: Config / Logging
# =========================================================

def cfg_file(land: str) -> str:
    p = os.path.join("Bekanntmachungen", f"config_{land}.ini")
    if os.path.exists(p):
        return p
    return f"config_{land}.ini"


def cfg_get(cfg, section: str, option: str, fallback: str = "") -> str:
    """Robust: cfg kann dict oder ConfigParser sein."""
    if isinstance(cfg, dict):
        try:
            return str(cfg.get(section, {}).get(option, fallback))
        except Exception:
            return str(fallback)

    # ConfigParser-ähnlich
    try:
        return str(cfg.get(section, option, fallback=fallback))
    except Exception:
        try:
            # fallback ohne keyword
            return str(cfg.get(section, option))
        except Exception:
            return str(fallback)


def log_line(msg: str):
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("protokoll.txt", "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def log_exc(prefix: str, e: Exception):
    log_line(f"{prefix}: {repr(e)}")
    log_line(traceback.format_exc())


def ensure_csv_exists(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([
                "Datum", "Aktenzeichen", "Gericht",
                "Schuldner", "Sitz", "Register", "VeroeffText"
            ])


def read_timeouts(cfg):
    def _get_int(section, option, default):
        try:
            return int(cfg_get(cfg, section, option, str(default)))
        except Exception:
            return int(default)

    wait_short = _get_int("timeouts", "wait_short", 30)
    wait_long  = _get_int("timeouts", "wait_long", 180)
    page_load  = _get_int("timeouts", "page_load", wait_long)

    # separat für den Text im Popup (soll nicht ewig hängen)
    veroeff_timeout = _get_int("timeouts", "veroeff_timeout", 45)

    # Stufe-2: wie viele VeröffText-Fehler IN FOLGE -> Tagesabbruch
    max_veroeff_fail_in_row = _get_int("timeouts", "max_veroeff_fail_in_row", 10)

    return wait_short, wait_long, page_load, veroeff_timeout, max_veroeff_fail_in_row


# =========================================================
# Popup Handling (ein Fenster wiederverwenden)
# =========================================================

def get_popup_handle(driver, main_handle: str, wait_long: int) -> str:
    WebDriverWait(driver, wait_long).until(lambda d: len(d.window_handles) >= 2)
    for h in driver.window_handles:
        if h != main_handle:
            return h
    raise RuntimeError("Popup-Fenster nicht gefunden")


def wait_popup_navigated(driver, popup_handle: str, old_url: str, timeout: int):
    def _changed(d):
        try:
            d.switch_to.window(popup_handle)
            cur = d.current_url
            return (cur is not None) and (cur != old_url)
        except Exception:
            return False

    WebDriverWait(driver, timeout).until(_changed)


def read_veroefftext_from_popup(driver, popup_handle: str, timeout: int) -> str:
    driver.switch_to.window(popup_handle)
    pre = WebDriverWait(driver, timeout).until(
        ec.presence_of_element_located((By.ID, "veroefftext"))
    )
    return pre.text


# =========================================================
# Main class
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

        # Stabilität: definierter Viewport
        options.add_argument("--width=1400")
        options.add_argument("--height=900")

        # Ressourcen sparen
        options.set_preference("permissions.default.image", 2)

        # Stabilität: weniger “focus”-Zicken
        options.set_preference("browser.tabs.remote.autostart", False)
        options.set_preference("browser.tabs.remote.autostart.2", False)

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

    def _set_datum_js(self, driver, wait, datum):
        """JSF-sicher: keine clear()/send_keys auf type=date, sondern JS setzen."""
        d = datum.strftime("%Y-%m-%d")

        von = wait.until(ec.presence_of_element_located(
            (By.ID, "frm_suche:ldi_datumVon:datumHtml5")
        ))
        bis = wait.until(ec.presence_of_element_located(
            (By.ID, "frm_suche:ldi_datumBis:datumHtml5")
        ))

        driver.execute_script("""
            arguments[0].scrollIntoView({block: 'center'});
            arguments[0].value = arguments[2];
            arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
            arguments[0].dispatchEvent(new Event('change', {bubbles:true}));

            arguments[1].scrollIntoView({block: 'center'});
            arguments[1].value = arguments[2];
            arguments[1].dispatchEvent(new Event('input', {bubbles:true}));
            arguments[1].dispatchEvent(new Event('change', {bubbles:true}));
        """, von, bis, d)

    # -----------------------------------------------------

    def starten_alle_tage(self):
        log_line("=== START AUSLESEN ===")
        log_line(f"CWD={os.getcwd()}")
        log_line(f"CSV={self.csv_ausl}")

        url = "https://neu.insolvenzbekanntmachungen.de/ap/suche.jsf"

        cfg = Config.daten_auslesen(cfg_file(self.land))
        wait_short, wait_long, page_load, veroeff_timeout, max_veroeff_fail_in_row = read_timeouts(cfg)

        firefox_path = cfg_get(cfg, "firefox", "pfad", "")
        headless_raw = cfg_get(cfg, "selenium", "headless", "1").strip().lower()
        headless = headless_raw in ("1", "true", "yes", "on")

        self.ausgabe.append(
            f"Timeouts: short={wait_short}s long={wait_long}s page_load={page_load}s "
            f"| veroeff_timeout={veroeff_timeout}s | max_fail_in_row={max_veroeff_fail_in_row} "
            f"| headless={1 if headless else 0}"
        )

        datum_bis = datetime.datetime.today() - datetime.timedelta(days=1)
        tage = (datum_bis - self.datum_von).days + 1

        for _ in range(tage):
            tag = self.datum_von.strftime("%d.%m.%Y")
            self.ausgabe.append(f"{tag}: starte Tag")
            log_line(f"{tag}: Tagstart")

            driver = None
            tag_ok = True

            try:
                # pro Tag neue Session (stabil)
                driver = self._make_driver(firefox_path, page_load, headless)
                main_handle = driver.current_window_handle
                popup_handle = None
                veroeff_fail_count = 0  # zählt Fehler IN FOLGE

                wait = self._open_search_and_set_land(driver, url, wait_long)

                # Datum setzen
                self._set_datum_js(driver, wait, self.datum_von)

                # Suchen klicken
                suchen = wait.until(ec.element_to_be_clickable((By.ID, "frm_suche:cbt_suchen")))
                driver.execute_script("arguments[0].click();", suchen)

                # Warten: Ergebnis-Tabelle oder "keine Treffer"
                def ready(d):
                    if d.find_elements(By.ID, "tbl_ergebnis"):
                        return True
                    src = d.page_source.lower()
                    return ("keine bekanntmachungen" in src or "keine treffer" in src or "keine ergebnisse" in src)

                WebDriverWait(driver, wait_long).until(ready)

                tables = driver.find_elements(By.ID, "tbl_ergebnis")
                if not tables:
                    self.ausgabe.append(f"{tag}: keine Bekanntmachungen")
                    log_line(f"{tag}: keine Bekanntmachungen")
                else:
                    # Anzahl Zeilen ermitteln (stabil)
                    table = driver.find_element(By.ID, "tbl_ergebnis")
                    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                    n = len(rows)
                    log_line(f"{tag}: Treffer={n}")

                    row_count = 0

                    with open(self.csv_ausl, "a", newline="", encoding="utf-8-sig") as f:
                        w = csv.writer(f, delimiter=";")

                        for i in range(n):
                            # Row jedes Mal neu holen (gegen Stale)
                            table = driver.find_element(By.ID, "tbl_ergebnis")
                            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                            if i >= len(rows):
                                # Tabelle hat sich unerwartet verändert -> Tag abbrechen
                                log_line(f"{tag}: Unerwartete Tabellenänderung (i={i}, rows={len(rows)})")
                                tag_ok = False
                                break

                            row = rows[i]

                            try:
                                datum_txt = row.find_element(By.CSS_SELECTOR, "span[id$=':otx_datum']").text
                                az        = row.find_element(By.CSS_SELECTOR, "span[id$=':otx_azAkt']").text
                                gericht   = row.find_element(By.CSS_SELECTOR, "span[id$=':otx_Gericht']").text
                                schuldner = row.find_element(By.CSS_SELECTOR, "span[id$=':otx_schuldner']").text
                                sitz      = row.find_element(By.CSS_SELECTOR, "span[id$=':otx_Sitz']").text
                                register  = row.find_element(By.CSS_SELECTOR, "span[id$=':otx_register']").text
                            except Exception as e:
                                log_line(f"{tag}: Kerndaten nicht gelesen (Zeile {i+1}): {repr(e)}")
                                tag_ok = False
                                break

                            # Lupe klicken -> Popup lädt neue Seite
                            veroeff = ""
                            try:
                                btn = row.find_element(By.CSS_SELECTOR, "input[alt='Veröffentlichungstext anzeigen']")

                                # alte Popup-URL merken, damit wir auf Navigation warten können
                                old_url = ""
                                if popup_handle is not None:
                                    try:
                                        driver.switch_to.window(popup_handle)
                                        old_url = driver.current_url or ""
                                    except Exception:
                                        popup_handle = None

                                driver.switch_to.window(main_handle)
                                driver.execute_script("arguments[0].click();", btn)

                                if popup_handle is None:
                                    popup_handle = get_popup_handle(driver, main_handle, wait_long)
                                    old_url = ""  # beim ersten Mal reicht "irgendwas"

                                # warten, dass Popup wirklich auf neue Seite navigiert
                                wait_popup_navigated(driver, popup_handle, old_url, veroeff_timeout)

                                # Text lesen
                                veroeff = read_veroefftext_from_popup(driver, popup_handle, veroeff_timeout)
                                veroeff_fail_count = 0  # Erfolg -> reset

                            except Exception as e:
                                veroeff = ""
                                veroeff_fail_count += 1
                                log_line(f"{tag}: VeröffText fehlgeschlagen (Zeile {i+1}, fail_in_row={veroeff_fail_count}): {repr(e)}")

                            finally:
                                # immer zurück ins Hauptfenster
                                try:
                                    driver.switch_to.window(main_handle)
                                except Exception:
                                    pass

                            # CSV schreiben (immer)
                            w.writerow([
                                datum_txt.replace(";", ","),
                                az.replace(";", ","),
                                gericht.replace(";", ","),
                                schuldner.replace(";", ","),
                                sitz.replace(";", ","),
                                register.replace(";", ","),
                                (veroeff or "").replace("\n", " ").replace(";", ",")
                            ])
                            row_count += 1

                            # Status
                            if row_count <= 20 or row_count % 100 == 0:
                                self.ausgabe.append(f"{tag}: {row_count}/{n}")

                            # flush crash-sicher
                            if row_count % 20 == 0:
                                f.flush()
                                try:
                                    os.fsync(f.fileno())
                                except Exception:
                                    pass

                            # Stufe-2: zu viele VeröffText-Fehler in Folge -> Tag abbrechen
                            if veroeff_fail_count >= max_veroeff_fail_in_row:
                                log_line(f"{tag}: Zu viele VeröffText-Fehler IN FOLGE ({veroeff_fail_count}) -> Tagesabbruch")
                                self.ausgabe.append(f"{tag}: Abbruch – zu viele VeröffText-Fehler in Folge ({veroeff_fail_count})")
                                tag_ok = False
                                break

                            # kleine Bremse
                            if row_count % 50 == 0:
                                time.sleep(0.15)

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

            # Datum/INI nur fortschreiben, wenn der Tag OK war
            if tag_ok:
                self.datum_von += datetime.timedelta(days=1)
                Config.schreiben(cfg_file(self.land), None, "insobm", "datum", self.datum_von.strftime("%d.%m.%Y"))
                log_line(f"{tag}: Tag OK -> Datum fortgeschrieben auf {self.datum_von.strftime('%d.%m.%Y')}")
            else:
                log_line(f"{tag}: Tag NICHT OK -> Datum bleibt {self.datum_von.strftime('%d.%m.%Y')}")
                # kontrollierter Abbruch der Gesamtschleife (du willst Fehler sehen, nicht drüberbügeln)
                break

        log_line("=== ENDE AUSLESEN ===")

