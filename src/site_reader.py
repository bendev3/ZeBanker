import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pickle
import os
from utils import log
#from utils import download_blob, upload_blob
import os


BASE_URL = "https://donkhouse.com/group"

class SiteReader:
    def __init__(self, group_id, download_dir, table_ids, num_recent_tables):
        log("Running SiteReader with group id {}, download dir {}, table ids {}, num tables {}".format(group_id, download_dir, table_ids, num_recent_tables), 1)
        self.group_id = group_id
        self.download_dir = download_dir
        self.table_ids = table_ids
        self.num_recent_tables = num_recent_tables
        self.output_dir = os.path.abspath(os.path.join(download_dir, "../"))
        #os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(self.output_dir, "My First Project-de2a72e48858.json")
        self.cookies = self.get_pickle_from_google_cloud("cookies.pkl")
        self.driver = None
        self.latest_tables = self.get_latest_tables()

    def init_selenium_driver(self):
        log("Initializing selenium driver with cookies.pkl file", 0)
        # For linux, start display
        chrome_options = Options()
        prefs = {"download.default_directory": self.download_dir}
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get('https://donkhouse.com/group/11395/44476')
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)

    def get_pickle_from_google_cloud(self, name):
        file_path = os.path.join(self.output_dir, name)
        #download_blob(name, file_path)
        return pickle.load(open(file_path, "rb"))

    def upload_pickle_to_google_cloud(self, object, name):
        file_path = os.path.join(self.output_dir, name)
        pickle.dump(object, open(file_path, "wb"))
        #upload_blob(file_path, name)

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
            log("Getting table(s) {} for group {}".format(self.table_ids, self.group_id), 0)
            return [table for table in self.get_tables() if table[0] in self.table_ids]
        if self.num_recent_tables is not None:
            log("Getting the most recent {} table(s) for group {}".format(self.num_recent_tables, self.group_id), 0)
            return self.get_tables()[-1 * self.num_recent_tables:]

        new_table_list = self.get_tables()
        old_table_list_filename = "old_tables_{}.pkl".format(self.group_id)  # Group specific table list
        try:
            old_tables = self.get_pickle_from_google_cloud(old_table_list_filename)
            new_tables = list(set(new_table_list) - set(old_tables))
            self.upload_pickle_to_google_cloud(new_table_list, old_table_list_filename)
            log("Found {} new tables since the last table backup. Tables: {}".format(len(new_tables), new_tables))
            return new_tables
        except Exception as e:
            log("Error: {}. Likely no table backup. Backing up current table list.".format(e))
            self.upload_pickle_to_google_cloud(new_table_list, old_table_list_filename)
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
            log("No tables to retrieve.")


"""
# run this once to store cookies for a login
def one_time_get_cookies():
    driver = webdriver.Chrome()
    driver.get('https://donkhouse.com/group/11395/44476')
    time.sleep(15)
    # manually enter user/password in the browser window
    pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))
"""