import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from utils import log, get_pickle, set_pickle
import argparse
import html2text

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
        self.init_selenium_driver()

    def init_selenium_driver(self):
        log("Initializing selenium driver with cookies.pkl file", 0)
        #chrome_options = Options()
        #chrome_options.add_argument("--headless")
        #self.driver = webdriver.Chrome(options=chrome_options)
        self.driver = webdriver.Chrome()
        self.driver.get(BASE_URL)
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)

    def open_any_table(self, table_id):
        #  Open one table which exposes the socket variable.
        #  Only needs to be done once, we can download results from any table once we're at any table
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

    def get_chat_history(self, table_id):
        self.open_any_table(table_id)
        for i in range(100):
            table_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            chat = table_soup.find('div', id='chat_group')
            chat_text = html2text.html2text(str(chat))
            if chat_text.strip() != '':
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
        return [chat for chat in chat_text.splitlines() if "came through" not in chat and chat != '']

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
            if old_msg == new_chat[0]:
                offset = 0
                for new_msg_index, new_msg in enumerate(new_chat):
                    if old_chat[old_msg_index + offset] == new_msg:
                        if old_msg_index + offset == len(old_chat) - 1:
                            log("Found overlap with old index {}/{} new index {}/{}".format(old_msg_index, len(old_chat), new_msg_index, len(new_chat)))
                            return old_chat + new_chat[new_msg_index + 1:]
                        offset += 1
                    else:
                        break

    def update_chat_for_table(self, table_id):
        old_chat_filename = "{}_{}_chat.pkl".format(self.group_id, table_id)
        old_chat = get_pickle(self.download_dir, old_chat_filename) if os.path.isfile(os.path.join(self.download_dir, old_chat_filename)) else None
        new_chat = self.get_chat_history(table_id)
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
        else:
            log("Chat has not changed for table {}".format(table_id))

    def log_chat(self, chat):
        return len(chat) if chat else None

    def get_active_tables(self):
        link = "{}/{}".format(BASE_URL, self.group_id)
        self.driver.get(link)
        self.driver.execute_script("socket.emit('request sitting count', 0)")
        time.sleep(1.0)  # wait to get sitting counts
        group_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        tables = group_soup.find_all('div', {'name': 'sitting'})
        active_tables = []
        for table in tables:
            log("Table html line {}".format(table), 3)
            if int(table.string.split("/")[0]) >= 2:  # 2 players needed to play
                active_tables.append(table.attrs["id"])
        return active_tables

    def run(self):
        for table_id in self.get_active_tables():
            log("{} is active, updating chat history".format(table_id))
            self.update_chat_for_table(table_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Files need to be downloaded from Donkhouse
    parser.add_argument('-group_id', default=11395, help="Group ID")
    parser.add_argument('-output_dir', default="../Output", help="Directory to output chat history to")

    args = parser.parse_args()
    log(args)

    logger = HistoryLogger(args.group_id, args.output_dir)
    while True:
        try:
            logger.run()
            time.sleep(300)  # sleep five minutes and grab the next chat
        except KeyboardInterrupt:
            log("Keyboard interrupt")
            logger.finish()
            break
        except Exception as e:
            log("Different Exception: {}".format(str(e)))
            # continue?
