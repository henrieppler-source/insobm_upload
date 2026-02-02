# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.common import exceptions
import datetime
import csv
from Scripte import Config


class Auslesen:
    def __init__(self, ausgabe):
        """
        Auslesen der Insolvenzbekanntmachungen.
        :param ausgabe: Textfeld auf dem Fenster (hier Ausgabefenster).
        """
        # Länder, die das Programm nutzen: ("Bremen", "4") | ("Hamburg", "5"),("Schleswig-Holstein", "14")
        # ("Hessen", "6")
        # restliche Länder: ("Bayern", "1") | ("Thüringen", "15") | ("Sachsen-Anhalt", "13") | ("Rheinland-Pfalz", "10")
        self.bundesland = [("Bayern", "1")]

        # Deklaration von Klassenvariablen
        self.land = self.bundesland[0][0]
        self.kennung = self.bundesland[0][1]  # Kennung des Bundeslandes
        self.csv_ausles = None  # Ausgabedatei
        self.driver = None  # Browser
        self.ausgabe = ausgabe  # Ausgabefenster
        self.datum_von = self.__datum_von()

        # Textausgabe im Ausgabefenster
        self.ausgabe.txt_edit.append(f'Auslesen wird begonnen: {datetime.datetime.today()}')

        # In einer Schleife die Liste der Länder durchgehen. Nord und Berlin-Brandburg bearbeiten 2 Länder.
        # Für diese werden separate Dateien angelegt
        for bundes_land in self.bundesland:
            # Erstellung der Parameter, Prozedur-Werte
            self.land = bundes_land[0]
            self.kennung = bundes_land[1]
            self.csv_ausl = "Bekanntmachungen/" + self.land + "_data.csv"
            self.starten()

        # Textausgabe im Ausgabefenster
        self.ausgabe.txt_edit.append(f'Auslesen abgeschlossen: {datetime.datetime.today()}')

    def __datum_von(self):
        """
        Ermittlung des ersten Auslesetages.
        Die Config-Datei besitzt die Sektion 'insobm' mit der Option 'datum'. Dieses Datum ist beim erstmaligen Start
        der Anwendung der 01.08.2018.
        :return: Datum des Auslesetages (Format datetime)
        """
        datei = f"config_{self.land}.ini"
        print(datei)
        datum_config = datetime.datetime.strptime(
            Config.daten_auslesen(datei)['insobm']['datum'], "%d.%m.%Y")
        return datum_config

    def __schreibe_datum(self, datum):
        """
        Eintragen der Datumsangaben in die Eingabefelder
        :param datum: Auslesedatum
        :return: None
        """
        wait = WebDriverWait(self.driver, 10)
        auslesedatum = datetime.datetime.strftime(datum, "%Y-%m-%d")

        # Datum_Von eintragen
        datum_von = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumVon:datumHtml5")))
        datum_von.clear()
        datum_von.send_keys(auslesedatum)

        # Datum_Bis eintragen
        datum_bis = wait.until(ec.presence_of_element_located((By.ID, "frm_suche:ldi_datumBis:datumHtml5")))
        datum_bis.clear()
        datum_bis.send_keys(auslesedatum)

    def starten(self):
        """
        Hier werden die Bekanntmachungen auf der neuen Seite der Insolvenzbekanntmachungen ausgelesen
        - Alle Verfahren ab 01.01.2018
        :return:
        """
        # Textausgabe im Ausgabefenster
        self.ausgabe.txt_edit.append(f"     Auslesen der neuen Verfahren wird gestartet.")

        # Variable für die Zahl der an einem Tag veröffentlichten Bekanntmachungen
        anz_bekannt = 0

        # URL zur Internetseite
        url = 'https://neu.insolvenzbekanntmachungen.de/ap/suche.jsf;' \
              'jsessionid=ekojD00f1qWGu-Y29cmRWcc96s6bL-dYtfFjRSYy.node-086 '

        # Enddatum bestimmen
        datum_bis = datetime.datetime.today() - datetime.timedelta(days=1)

        # Anzahl auszulesender Tage ermitteln
        anz_tage = (datum_bis - self.datum_von + datetime.timedelta(days=1)).days

        # prüfen, ob ausgelesen werden muss
        if not anz_tage < 1:
            self.ausgabe.txt_edit.append(f"     Auslesen wird gestartet... \n     "
                                         f"Für {anz_tage} Tag(e) werden die Bekanntmachungen ausgelesen")

            # Arrays anlegen
            arr_temp_werte = []  # Werte werden nur vorübergehend hier gespeichert
            arr_werte = []

            # Browser initialisieren
            options = Options()  # Optionen für den Browser anlegen
            config = Config.daten_auslesen(r"Bekanntmachungen/config_" + self.land + ".ini")  # Pfad zum Browser holen
            options.binary_location = r'{0}'.format(config['firefox']['pfad'])  # Pfad als Option festlegen
            self.driver = webdriver.Firefox(options=options)  # Firefox als Browser mit Optionen festlegen und starten
            # URL aufrufen
            self.driver.get(url)  # zur URL gehen

            # Wartezeit einstellen
            wait = WebDriverWait(self.driver, 10)

            # Bundesland einstellen
            option_land = wait.until(ec.element_to_be_clickable((
                By.XPATH, f"//select[@name='frm_suche:lsom_bundesland:lsom']/option[@value='{self.kennung}']")))
            option_land.click()

            # Für jeden Tag seit 'datum_von' die Bekanntmachungen auslesen
            for auslesetag in range(anz_tage):

                # Datum in die Felder eintragen
                self.__schreibe_datum(self.datum_von)

                try:

                    # Die Schaltfläche "Suchen" auswählen
                    suchen_klick = wait.until(ec.element_to_be_clickable((By.ID, "frm_suche:cbt_suchen")))

                    # Wenn die "Suchen"-Schaltfläche gefunden wurde, dann anklicken
                    self.driver.execute_script("arguments[0].click();", suchen_klick)

                # Wenn es zu einer Fehlemeldung kommen sollte, wird diese im Ausgabefenster angezeigt
                except Exception as e:
                    self.ausgabe.txt_edit.append(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

                # prüfen, ob für das Datum Bekanntmachungen vorhanden sind
                try:
                    # TODO: Hier nicht warten, sondern schauen, welcher Text angezeigt wird.
                    # Warten, bis die Tabelle geladen ist

                    table = wait.until(ec.presence_of_element_located((By.ID, "tbl_ergebnis")))

                    # Alle Zeilen der Tabelle finden
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for i in range(1, len(rows)):

                        # Tabellenwerte auslesen
                        datum_neu = self.driver.find_element(By.CSS_SELECTOR,
                                                             f"[id='tbl_ergebnis\\:{i - 1}\\:otx_datum']").text
                        arr_temp_werte.append(datum_neu)
                        datum_neu = ""
                        aktenzeichen_neu = self.driver.find_element(By.CSS_SELECTOR,
                                                                    f"#tbl_ergebnis\\:{i - 1}\\:otx_azAkt").text
                        arr_temp_werte.append(aktenzeichen_neu)
                        aktenzeichen_neu = ""
                        gericht_neu = "{0}".format(self.driver.find_element(
                            By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i - 1}\\:otx_Gericht").text)
                        arr_temp_werte.append(gericht_neu.replace(",", ";"))
                        gericht_neu = ""
                        schuldner_neu = "{0}".format(
                            self.driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i - 1}\\:otx_schuldner").text)
                        arr_temp_werte.append(schuldner_neu.replace(",", ";"))
                        schuldner_neu = ""
                        sitz_neu = self.driver.find_element(By.CSS_SELECTOR, f"#tbl_ergebnis\\:{i - 1}\\:otx_Sitz").text
                        arr_temp_werte.append("{0}".format(sitz_neu).replace(",", ";"))
                        sitz_neu = ""
                        register_neu = self.driver.find_element(By.CSS_SELECTOR,
                                                                f"#tbl_ergebnis\\:{i - 1}\\:otx_register").text
                        arr_temp_werte.append("{0}".format(register_neu).replace(",", ";"))
                        register_neu = ""

                        # zum Veröffentlichungstext wechseln
                        # aktuelles Fenster speichern
                        window_now = self.driver.window_handles[0]
                        text_anzeige = wait.until(ec.element_to_be_clickable((
                            By.XPATH,
                            f"(//input[contains(@id, 'frm_detail:j_idt') and @type='image' and "
                            f"@alt='Veröffentlichungstext anzeigen'])[{i}]")))
                        self.driver.execute_script("arguments[0].click();", text_anzeige)
                        window_after = self.driver.window_handles[1]
                        self.driver.switch_to.window(window_after)

                        # Bekanntmachungstext auslesen
                        veroefftext = wait.until(ec.presence_of_element_located((
                            By.XPATH, ".//pre[@id='veroefftext']"))).text

                        # Bekanntmachungstext formatieren
                        veroeff_text = "{0}".format(veroefftext).replace("\n", " ").replace(
                            ",", ";").encode("utf_8").decode('utf_8')
                        veroefftext = ""
                        arr_temp_werte.append(veroeff_text)
                        veroeff_text = ""
                        arr_werte.append(arr_temp_werte)
                        self.driver.close()
                        self.driver.switch_to.window(window_now)
                        self.ausgabe.txt_edit.append(f"     {arr_temp_werte[0]}  -  {arr_temp_werte[1]}  -  "
                                                     f"{arr_temp_werte[3]}")
                        arr_temp_werte = []
                        anz_bekannt += 1

                    # Wenn alle Bekanntmachungen ausgelesen wurden, eine Seite zurück
                    zurueck = wait.until(ec.element_to_be_clickable((By.XPATH, ".//input[@value='Zurück']")))
                    zurueck.click()

                    # generierte Daten in die csv-Datei speichern
                    with open(self.csv_ausl, "a", newline="", encoding="utf-8") as file:
                        writer = csv.writer(file)
                        for rows in arr_werte:
                            writer.writerow(rows)
                    print(arr_werte)

                    # Array leeren
                    arr_werte = []

                    # Datum hoch zählen
                    self.datum_von = self.datum_von + datetime.timedelta(days=1)

                    # ini-Datei anpassen
                    Config.schreiben(datei=r"Bekanntmachungen/config_" + self.land + ".ini",
                                     config=config,
                                     sektion='insobm',
                                     option='datum',
                                     wert=datetime.date.strftime(self.datum_von, "%d.%m.%Y"))

                    # Anzahl der ausgegebenen Daten anzeigen
                    self.ausgabe.txt_edit.append(f"     Anzahl ausgelesener Daten an diesem Tag: {anz_bekannt}")
                    anz_bekannt = 0

                # wenn keine Bekanntmachungen vorhanden sind, dann auf die Übersichtsseite zurückgehen
                # und ini-Datei anpassen
                except exceptions.TimeoutException:
                    try:
                        zurueck = wait.until(ec.element_to_be_clickable((By.XPATH, ".//input[@value='Zurück']")))
                        zurueck.click()
                        self.ausgabe.txt_edit.append(f"     {datetime.date.strftime(self.datum_von, '%d.%m.%Y')}: "
                                                     f"Heute keine Bekanntmachungen")
                        self.datum_von = self.datum_von + datetime.timedelta(days=1)
                        Config.schreiben(datei=r"Bekanntmachungen/config_" + self.land + ".ini",
                                         config=config,
                                         sektion='insobm',
                                         option='datum',
                                         wert=datetime.date.strftime(self.datum_von, "%d.%m.%Y"))
                    except exceptions.TimeoutException:
                        self.driver.back()
                        anz_tage = anz_tage + 1
                        self.ausgabe.txt_edit.append(f"     SAFE-Anmeldung aufgetaucht")
            self.driver.quit()

        # Falls nicht mindestens 1 Tag Unterschied ist, dann wurde schon ausgelesen
        else:
            self.ausgabe.txt_edit.append(f"     Es wurden bereits Daten ausgelesen.")
