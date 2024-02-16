import configparser
import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import sys
import shutil
import re




#current directory
dir_path = os.path.dirname(os.path.abspath(sys.argv[0]))

#Fehler Logging
def log_errors_to_file(error_message, file_path= (dir_path+"/Report.log")):
    # Öffne die Datei im Anhangsmodus (a für append)
    with open(file_path, 'a') as error_file:
        # Schreibe die Fehlermeldung in die Datei
        error_file.write(f"{error_message}\n")


#löscht die Datei wenn Sie älter als x Tage ist
def delete_old_file(max_age_in_days):
    current_time = time.time()
    max_age_in_seconds = max_age_in_days * 24 * 60 * 60  # Umrechnung von Tagen in Sekunden
    file_path = './Report.log'

    try:
        # Überprüfe, ob es sich um eine Datei handelt
        if os.path.isfile(file_path):
            # Berechne das Alter der Datei
            file_age = current_time - os.path.getctime(file_path)

            # Lösche die Datei, wenn sie älter ist als die angegebene Zeit
            if file_age > max_age_in_seconds:
                os.remove(file_path)
                e = ("Datei "+file_path+" gelöscht, da sie älter als "+max_age_in_days+" Tage ist.")
                log_errors_to_file(e)
            else:
                e = ("Datei "+file_path+" ist nicht älter als "+max_age_in_days+" Tage. Daher wird Sie nicht gelöscht")
                log_errors_to_file(e)

    except Exception as e:
        log_errors_to_file(e)


def read_ini_variable(section, variable):
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    try:
        # Read the INI file
        config.read(dir_path+"/config.ini")
        #config.read("e:\FELIOS-SUPPORT\Entwicklung_Support\GitRelease\Config\config.ini")

        # Access the variable from the specified section
        value = config.get(section, variable)
        return value
    except configparser.NoSectionError:
        e = (f"Error: Section '{section}' nicht in der config.ini vorhanden \n")
        log_errors_to_file(e)
    except configparser.NoOptionError:
        e = (f"Error: Variable '{variable}' nicht in der Section '{section}' innerhalb der config.ini gefunden. \n")
        log_errors_to_file(e)
    except Exception as e:
        log_errors_to_file(e)


#get latest Github Release
def get_releases(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None
 

#Liest eine Website aus gibt den ersten Link mit dem gesuchten Keyword zurück
def get_first_link(url, target_keyword):
    try:
        # Webseite abrufen
        response = requests.get(url)
        response.raise_for_status()  # Fehler behandeln

        # BeautifulSoup verwenden, um die Webseite zu analysieren
        soup = BeautifulSoup(response.text, 'html.parser')

        # Den ersten Link mit dem bestimmten Keyword finden
        link = soup.find('a', href=lambda href: href and target_keyword in href)

        if link:
            e = urljoin(url, link['href'])
            log_errors_to_file(e)
            return e
        else:
            return None

    except Exception as e:
        log_errors_to_file(e)
        return None


def get_last_segment(url):
    segments = url.split('/')
    last_segment = segments[-1]
    return last_segment


def download_file_extern(url, destination):
    response = requests.get(url)
    
    if response.status_code == 200:
        with open(destination, 'wb') as file:
            file.write(response.content)
        e = ("Downloaded "+url+" nach "+destination)
        log_errors_to_file(e)
    else:
        e = ("Konnte nicht Heruntergeladen werden" + url+". Status code: "+response.status_code+"\n")
        log_errors_to_file(e)


def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename
 

def separate_and_copy_files(first_string, combined_string):
    # Suche den Index, an dem der erste String endet
    index = combined_string.find(first_string)

    # Trenne den zweiten String am gefundenen Index
    if index != -1:
        second_string = combined_string[index + len(first_string):]
        file_name, file_extension = os.path.splitext(second_string)

        # Entferne alle Zeichen außer Buchstaben aus dem Dateinamen
        letters_only = re.sub(r'[^a-zA-Z]', '', file_name)

        # Erstelle den neuen Dateipfad mit dem bearbeiteten Dateinamen und der ursprünglichen Dateiextension
        new_file_path = os.path.join(first_string, letters_only + file_extension)

        try:
            # Kopiere die Datei mit dem bearbeiteten Dateinamen an den neuen Pfad
            shutil.copy(combined_string, new_file_path)
            os.remove(combined_string)
            return new_file_path
        except shutil.SameFileError:
            # Ignoriere SameFileError und gib den ursprünglichen zweiten String zurück
            return combined_string
    else:
        # Gib den ursprünglichen zweiten String zurück, falls der erste String nicht gefunden wurde
        return combined_string

if __name__ == "__main__":

    #löschen der alten Log Datei
    section_name = "Settings"
    max_age_in_days = read_ini_variable(section_name, 'delete_after_days')
    delete_old_file(max_age_in_days)


    # INI-Datei laden
    config = configparser.ConfigParser()
    config.read(dir_path+"/config.ini")


    # Variablen als Listen initialisieren
    owner_list = []
    repo_list = []
    ending_list = []
    url_list = []
    key_list = []
    downloadpath_git_list = []
    downloadpath_extern_list = []

    # Iteration durch die INI-Datei
    for section_name in config.sections():
        for option_name in config.options(section_name):
            key = f'{section_name}_{option_name}'
            value = config.get(section_name, option_name)

            # Überprüfen und Hinzufügen zu den entsprechenden Listen
            if 'owner' in key.lower():
                owner_list.append(value)
            elif 'repo' in key.lower():
                repo_list.append(value)
            elif 'ending' in key.lower():
                ending_list.append(value)
            elif 'url' in key.lower():
                url_list.append(value)
            elif 'key' in key.lower():
                key_list.append(value)
            elif 'downloadpath_git' in key.lower():
                downloadpath_git_list.append(value)
            elif 'downloadpath_extern' in key.lower():
                downloadpath_extern_list.append(value)


    #Runterladen der Git Releases 
    # Iteration durch die Listen und Ausführung des Codes für jeden Eintrag
    for owner, repo, ending, downloadpath_git in zip(owner_list, repo_list, ending_list, downloadpath_git_list):
        releases = get_releases(owner, repo)
        if releases:
            latest_release = releases[0]  # Erste Veröffentlichung in der Liste
            e = ("Die aktuelle Version von "+repo+" ist:", latest_release['tag_name'])
            log_errors_to_file(e)
            exe_file = None
            for asset in latest_release.get("assets", []):
                if asset['name'].endswith(ending):
                    exe_file = asset
                    break

            path = (downloadpath_git+"/"+exe_file['name'])

            if exe_file:
                e = ("Download-Link für das 64-Bit .exe Asset:", exe_file['browser_download_url'])
                log_errors_to_file(e)
                download_path = download_file(exe_file['browser_download_url'], path)
                result = separate_and_copy_files(downloadpath_git, download_path)
                e = ("Datei heruntergeladen und gespeichert unter:", result)
                log_errors_to_file(e)
                e = "\n"
                log_errors_to_file(e)
            else:
                e = ("Keine 64-Bit .exe-Datei in dieser Veröffentlichung gefunden")
                log_errors_to_file(e)
                e = "\n"
                log_errors_to_file(e)
        else:
            e = ("Fehler beim Abrufen der Veröffentlichungen")
            log_errors_to_file(e)
            e = "\n"
            log_errors_to_file(e)


    #Runterladen externer Programme
    for url, key, downloadpath_extern in zip(url_list, key_list, downloadpath_extern_list):
        url_download = get_first_link(url, key)
        program_name = get_last_segment(url_download)
        destination_path = downloadpath_extern+"/"+program_name
        download_file_extern(url_download, destination_path)
        result = separate_and_copy_files(downloadpath_extern, destination_path)
        e = ("Datei heruntergeladen und gespeichert unter:", result)
        log_errors_to_file(e)
        e = "\n"
        log_errors_to_file(e)

    log_errors_to_file("Script beendet")
    log_errors_to_file("--------------")
