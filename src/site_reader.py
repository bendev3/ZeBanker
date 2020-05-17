import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pickle
import os
from utils import log
import os

class SiteReader:
    def __init__(self, group_id, num_recent_tables, download_dir):
        self.group_id = group_id
        self.num_recent_tables = num_recent_tables
        self.download_dir = download_dir
        self.output_dir = os.path.abspath(os.path.join(download_dir, "../"))
        self.base_url = "https://donkhouse.com/group"
        self.cookies = pickle.load(open(os.path.join(self.output_dir, "cookies.pkl"), "rb"))
        self.driver = None
        self.latest_tables = self.get_latest_tables()

    def init_selenium_driver(self):
        log("Initializing selenium driver with cookies.pkl file", 0)
        chrome_options = Options()
        prefs = {"download.default_directory": self.download_dir}
        chrome_options.add_experimental_option("prefs", prefs)
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get('https://donkhouse.com/group/11395/44476')
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)

    def get_tables(self):
        tables = []
        group_url = "{}/{}".format(self.base_url, self.group_id)
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
        if self.num_recent_tables is not None:
            log("Getting the most recent {} table(s) for group {}".format(self.num_recent_tables, self.group_id), 0)
            return self.get_tables()[-1 * self.num_recent_tables:]

        old_table_list_filename = "old_tables.pkl"
        new_table_list = self.get_tables()
        try:
            old_table_list = pickle.load(open(os.path.join(self.output_dir, old_table_list_filename), "rb"))
            new_tables = list(set(new_table_list) - set(old_table_list))
            pickle.dump(new_table_list, open(old_table_list_filename, "wb"))
            log("Found {} new tables since the last table backup. Tables: {}".format(len(new_tables), new_tables))
            return new_tables
        except Exception as e:
            log("Error: {}. Likely no table backup. Backing up current table list.".format(e))
            pickle.dump(new_table_list, open(os.path.join(self.output_dir, old_table_list_filename), "wb"))
            return []

    def click_download_csv(self, table_id):
        self.driver.get('https://donkhouse.com/group/{}/{}'.format(self.group_id, table_id))
        time.sleep(3)  # wait for the browser/site to load before running the script
        script = "socket.emit('download chip history request', {table_id:" + str(table_id) + "})"
        log("executing script:{}".format(script), 1)
        self.driver.execute_script(script)
        time.sleep(2)  # keep the browser open long enough to receive the csv from Donkhouse

    def finish(self):
        log("Quitting driver", 0)
        self.driver.quit()

    def run(self):
        log("Running site reader")
        if len(self.latest_tables) > 0:
            try:
                self.init_selenium_driver()
                for table_id, table_name in self.latest_tables:
                    log("Attempting to download csv for group {}, table {}:{}".format(self.group_id, table_id, table_name), 0)
                    self.click_download_csv(table_id)
            except Exception as e:
                log("Exception: {}".format(e))
            self.finish()
        else:
            log("No new tables to retrieve.")

"""
# run this once to store cookies for a specific login
def one_time_get_cookies():
    driver = webdriver.Chrome()
    driver.get('https://donkhouse.com/group/11395/44476')
    time.sleep(15)
    # manually enter user/password in the browser window
    pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))
"""