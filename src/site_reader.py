import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from utils import log, get_pickle, set_pickle

BASE_URL = "https://donkhouse.com/group"

class SiteReader:
    def __init__(self, group_id, download_dir, table_ids, num_recent_tables):
        log("Running SiteReader with group id {}, download dir {}, table ids {}, num tables {}".format(group_id, download_dir, table_ids, num_recent_tables), 1)
        self.group_id = group_id
        self.download_dir = download_dir
        self.table_ids = table_ids
        self.num_recent_tables = num_recent_tables
        self.output_dir = os.path.abspath(os.path.join(download_dir, "../"))
        self.cookies = get_pickle(self.output_dir, "cookies.pkl")
        self.driver = None
        self.latest_tables = self.get_latest_tables()
        self.num_files_retrieved = 0

    def init_selenium_driver(self):
        log("Initializing selenium driver with cookies.pkl file", 0)
        # For linux, start display
        chrome_options = Options()
        prefs = {"download.default_directory": self.download_dir,
                 "profile.default_content_setting_values.automatic_downloads": 1}
        chrome_options.add_experimental_option("prefs", prefs)
        #chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get(BASE_URL)
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)

    def get_tables(self):
        tables = []
        group_url = "{}/{}".format(BASE_URL, self.group_id)
        s = requests.Session()
        for cookie in self.cookies:
            s.cookies.set(cookie['name'], cookie['value'])
        page = s.get(group_url)
        group_soup = BeautifulSoup(page.text, 'html.parser')
        for f in group_soup.find_all('form', action="/group/{}".format(self.group_id)):
            a = f.find('a')
            if a:
                table_id = str(a['href']).split("/")[-1]
                table_name = str(a.find('u').get_text())
                tables.append((table_id, table_name))
        return tables

    def get_latest_tables(self):
        if self.table_ids is not None:
            log("Getting results from table(s) {} for group {}".format(self.table_ids, self.group_id), 0)
            return [table for table in self.get_tables() if table[0] in self.table_ids]
        if self.num_recent_tables is not None:
            log("Getting results from the most recent {} table(s) for group {}".format(self.num_recent_tables, self.group_id), 0)
            all_tables = self.get_tables()
            if self.num_recent_tables > len(all_tables):
                log("Running on all tables: {}".format(all_tables))
                return all_tables
            else:
                return all_tables[-1 * self.num_recent_tables:]

        log("Getting results from all tables since last table backup")
        new_table_list = self.get_tables()
        old_table_list_filename = "old_tables_{}.pkl".format(self.group_id)  # Group specific table list
        try:
            old_tables = get_pickle(self.output_dir, old_table_list_filename)
            new_tables = list(set(new_table_list) - set(old_tables))
            set_pickle(new_table_list, self.output_dir, old_table_list_filename)
            log("Found {} new tables since the last table backup. Tables: {}".format(len(new_tables), new_tables))
            return new_tables
        except Exception as e:
            log("Error: {}. Likely no table backup. Backing up current table list for future run.".format(e))
            set_pickle(new_table_list, self.output_dir, old_table_list_filename)
            return []

    def open_any_table(self, table_id):
        #  Open one table which exposes the socket variable.
        #  Only needs to be done once, we can download results from any table once we're at any table
        link = 'https://donkhouse.com/group/{}/{}'.format(self.group_id, table_id)

        log("Launching link {}".format(link))
        self.driver.get(link)

        # Wait until we have an accessible download button, meaning the site is loaded
        for i in range(300):
            try:
                self.driver.execute_script("game.info_widget.download_button")  # check if we have a download button
                break  # super hacky but if we do have a download button break the loop and continue
            except Exception as e:
                log("Site not loaded yet", 2)
            time.sleep(0.2)

    def click_download_csv(self, table_id):
        script = "socket.emit('download chip history request', {table_id:" + str(table_id) + "})"
        log("executing script:{}".format(script), 1)
        self.driver.execute_script(script)

        # Now wait for the directory to be created if it doesn't exist
        if not os.path.exists(self.download_dir):
            for i in range(600):
                if not os.path.exists(self.download_dir):
                    log("Download directory does not exist", 2)
                    time.sleep(0.1)
                else:
                    break

        # now wait for the file to exist
        for i in range(600):
            if self.num_files_retrieved >= len(os.listdir(self.download_dir)):
                log("Next file not loaded yet", 2)
                time.sleep(0.1)  # wait for file to download
            else:
                break

        self.num_files_retrieved += 1  # another file was retrieved
        log("So far we have retrieved {} files(s)".format(self.num_files_retrieved))

    def finish(self):
        log("Quitting driver", 0)
        self.driver.quit()

    def print_info_retrieved(self):
        s = "Retrieved results for table(s): "
        for t in self.latest_tables:
            s += t[1] + ", "
        return s[:-2]

    def run(self):
        if len(self.latest_tables) > 0:
            try:
                self.init_selenium_driver()
                self.open_any_table(self.latest_tables[0][0])  # open the first table
                for table_id, table_name in self.latest_tables:
                    log("Attempting to download csv for group {}, table {}:{}".format(self.group_id, table_id, table_name), 0)
                    self.click_download_csv(table_id)
            except Exception as e:
                log("Exception: {}".format(e))
            self.finish()
        else:
            log("No tables to retrieve.")

        if len(self.latest_tables) > 0:
            log("Asserting {} files exist in {}".format(self.num_files_retrieved, self.download_dir))
            assert os.path.exists(self.download_dir), "Asserting download directory {} exists".format(self.download_dir)
            assert len(os.listdir(self.download_dir)) == len(self.latest_tables), \
                "Checking that num files {} equals num tables {}".format(len(os.listdir(self.download_dir)), len(self.latest_tables))

        return [self.print_info_retrieved()]


"""
# run this once to store cookies for a login
from selenium import webdriver
import pickle
import time
driver = webdriver.Chrome()
driver.get('https://donkhouse.com/group/11395/44476')
time.sleep(15)
# manually enter user/password in the browser window
pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))
"""