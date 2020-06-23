import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from utils import log, get_pickle, set_pickle
import argparse
import html2text
from datetime import datetime

BASE_URL = "https://donkhouse.com/group"
script_path = os.path.dirname(os.path.abspath(__file__))


class HistoryLogger:
    def __init__(self, group_id, output_dir):
        log("Running HistoryLogger with group id {}, output dir {}".format(group_id, output_dir), 1)
        self.group_id = group_id
        self.output_dir = os.path.join(script_path, output_dir)
        self.download_dir = os.path.join(script_path, self.output_dir, "ChatHistories")
        if not os.path.exists(self.download_dir):
            os.mkdir(self.download_dir)
        self.cookies = get_pickle(self.output_dir, "cookies.pkl")
        self.driver = None
        self.driver = self.init_selenium_driver()
        self.last_new_chat_lengths = {}
        self.last_active_tables = None

    def init_selenium_driver(self):
        log("Initializing selenium driver with cookies.pkl file", 0)
        chrome_options = Options()
        #chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(BASE_URL)
        for cookie in self.cookies:
            driver.add_cookie(cookie)
        return driver

    def open_any_table(self, table_id):
        link = '{}/{}/{}'.format(BASE_URL, self.group_id, table_id)
        log("Launching link {}".format(link))
        self.driver.get(link)
        # Wait until we have an accessible download button, meaning the site is loaded
        for i in range(120):
            try:
                self.driver.execute_script("game.info_widget.download_button")  # check if we have a download button
                break  # super hacky but if we do have a download button break the loop and continue
            except Exception as e:
                log("Site not loaded yet", 2)
            time.sleep(0.5)

    def get_chat_history(self, table_id, ignore_last):
        self.open_any_table(table_id)
        script = "update_chat_mode(\"hand histories only\")"
        log("Executing script {}".format(script))
        self.driver.execute_script(script)
        for i in range(30):
            table_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            chat = table_soup.find('div', id='chat_group')
            chat_text = html2text.html2text(str(chat))
            if chat_text.strip() != '' and chat_text.strip() != None:
                log("Chat text exists")
                break
            else:
                log("Get chat try number {} failed".format(i+1))
            time.sleep(0.2)
        '''
        if chat_text.strip() == '':
            script = "socket.emit('reinit chat',{})".format(table_id)
            log("No chat text, executing script: {}".format(script))
            self.driver.execute_script(script)
            return self.get_chat_history(table_id)  # try again, hope for no infinite recursion
        '''
        new_chat = [chat for chat in chat_text.splitlines() if "came through" not in chat and chat != '']
        if len(new_chat) > ignore_last:
            return new_chat[:len(new_chat) - ignore_last]
        return new_chat

    def finish(self):
        log("Quitting driver", 0)
        self.driver.quit()

    def consolodate_chats(self, old_chat, new_chat):
        if not new_chat and not old_chat:
            return None
        if not old_chat:
            return new_chat
        if not new_chat:
            return old_chat
        for old_msg_index, old_msg in enumerate(old_chat):
            if old_msg.strip() == new_chat[0].strip():
                for new_msg_index, new_msg in enumerate(new_chat):
                    if old_chat[old_msg_index + new_msg_index].strip() == new_msg.strip():
                        if old_msg_index + new_msg_index == len(old_chat) - 1:
                            log("Found overlap with old index{}/len{} new index{}/len{}".format(old_msg_index, len(old_chat), new_msg_index, len(new_chat)))
                            return old_chat + new_chat[new_msg_index + 1:]
                    else:
                        break

    def update_chat_for_table(self, table_id, ignore_last):
        old_chat_filename = "{}_{}_chat.pkl".format(self.group_id, table_id)
        old_chat = get_pickle(self.download_dir, old_chat_filename) if os.path.isfile(os.path.join(self.download_dir, old_chat_filename)) else None
        new_chat = self.get_chat_history(table_id, ignore_last)
        len_new_chat = len(new_chat)
        if table_id in self.last_new_chat_lengths:
            last_new_chat_length = self.last_new_chat_lengths[table_id]
        else:
            last_new_chat_length = None
        if len_new_chat > 400 or (last_new_chat_length is not None and len_new_chat >= last_new_chat_length * 1.7 and last_new_chat_length > 110):
            new_chat = []
            log("New chat length {} exceeds 1.7x the last new chat length {} or max 400. Ignoring.".format(
                len_new_chat, last_new_chat_length
            ))
        else:
            log("New chat length {} does not exceed 1.7x last new chat length {} or max 400. Using new chat.".format(
                len_new_chat, last_new_chat_length
            ))
            self.last_new_chat_lengths[table_id] = len(new_chat)
        log("Old chat length for table {}: {}".format(table_id, self.log_chat(old_chat)))
        log("New chat length for table {}: {}".format(table_id, self.log_chat(new_chat)))
        if old_chat != new_chat:
            consolodated_chat = self.consolodate_chats(old_chat, new_chat)
            if consolodated_chat is not None and len(consolodated_chat) > 0:
                log("Saving consolodated chat for table {}, length {}, first message {}, last message {}".format(
                    table_id, self.log_chat(consolodated_chat), consolodated_chat[0], consolodated_chat[len(consolodated_chat) - 1]))
                set_pickle(consolodated_chat, self.download_dir, old_chat_filename)
            else:
                log("Consolodated chat for table {} is None or len 0. Not saving.".format(table_id))
                log("Old:{}\n".format(old_chat))
                log("New:{}\n".format(new_chat))
                if len(old_chat) > 20:
                    log("End of old:{}\n".format(old_chat[-20:]))
                if len(new_chat) > 20:
                    log("Beginning of new:{}\n".format(new_chat[:20]))
                log("Consolodated:\n{}".format(consolodated_chat))
            if consolodated_chat is None or len(consolodated_chat) == 0 or not new_chat:
                # Situations where we fail, but want to run again, just run again rather than waiting
                log("Re running self.update_chat_for_table for table {} in 5 seconds".format(table_id))
                time.sleep(5)
                self.update_chat_for_table(table_id, ignore_last)
        else:
            log("Chat has not changed for table {}".format(table_id))

    def log_chat(self, chat):
        return len(chat) if chat else None

    def get_active_tables(self):
        link = "{}/{}".format(BASE_URL, self.group_id)
        log("Launching link {}".format(link))
        self.driver.get(link)
        script = "socket.emit('request sitting count', 0)"
        log("Executing script: {}".format(script))
        self.driver.execute_script(script)
        time.sleep(0.5)
        for i in range(30):
            group_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            tables = group_soup.find_all('div', {'name': 'sitting'})
            active_tables = []
            try:
                for table in tables:
                    log("Table html line {}".format(table), 3)
                    if int(table.string.split("/")[0]) >= 1:
                        active_tables.append(table.attrs["id"])
                break
            except Exception as e:
                log("Exception retrieving table counts trying again in 1.0s: {}".format(str(e)))
                time.sleep(1.0)
        return active_tables

    def run(self):
        log("Starting run")
        active_tables = self.get_active_tables()
        for table_id in active_tables:
            log("{} is active, updating chat history".format(table_id))
            self.update_chat_for_table(table_id, 15)
        if self.last_active_tables:
            recently_completed_tables = list(set(self.last_active_tables) - set(active_tables))
            for table_id in recently_completed_tables:
                log("Table {} is no longer active. Getting last set of messages.".format(table_id))
                self.update_chat_for_table(table_id, 0)
        self.last_active_tables = active_tables
        if len(active_tables) == 0:
            log("No active tables")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Files need to be downloaded from Donkhouse
    parser.add_argument('-group_id', default=11395, help="Group ID")
    parser.add_argument('-output_dir', default="../Output", help="Directory to output chat history to")
    parser.add_argument('-poll_interval', default="150", help="Time to wait between runs")

    args = parser.parse_args()
    log(args)

    while True:
        try:
            logger = HistoryLogger(args.group_id, args.output_dir)
            start = datetime.now()
            logger.run()
            logger.finish()
            finish = datetime.now()
            elapsed = (finish - start).total_seconds()
            time_to_sleep = float(args.poll_interval) - elapsed
            log("elapsed: {} seconds".format(elapsed))
            if time_to_sleep > 0:
                log("Sleeping {} seconds".format(time_to_sleep))
                time.sleep(time_to_sleep)
            else:
                log("Not sleeping")
        except KeyboardInterrupt:
            log("Keyboard interrupt")
            logger.finish()
            break
        except Exception as e:
            log("Different Exception: {}".format(str(e)))
            # continue?
