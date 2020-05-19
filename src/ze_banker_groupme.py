from poker_split import PokerSplit
from site_reader import SiteReader
from datetime import datetime
import requests
from utils import log
import os
import argparse
import re
import time

# Legit
#BOT_ID = "e4808a5a0d7f8fd6ec06fe42bc"
# Test
BOT_ID = "89997e88121f3d04ed8f9a7a2f"
API_ENDPOINT = "https://api.groupme.com/v3/bots/post"

class zeBanker:
    def __init__(self, arguments):
        self.files = arguments.files
        self.group_id = arguments.group_id
        self.output_dir = arguments.output_dir
        self.message = arguments.message

        self.num_tables = arguments.num_tables
        self.table_ids = arguments.table_ids

    def run(self):
        if self.files:
            log("files argument provided, running on existing files")
            msgs = banker.run_local()
        else:
            log("files argument not provided, retrieving files from Donkhouse")
            msgs = banker.run_external()

        if self.message:
            self.send_groupme_messages(msgs)
        else:
            for msg in msgs:
                print(msg)

    def run_local(self):
        ps = PokerSplit(self.files)
        return ps.run()

    def run_external(self):
        log("Attempting to get results from Donkhouse")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        script_path = os.path.dirname(os.path.abspath(__file__))
        download_dir = os.path.abspath(os.path.join(*[script_path, self.output_dir, timestamp]))

        site_reader = SiteReader(self.group_id, download_dir, self.table_ids, self.num_tables)
        site_reader_output = site_reader.run()
        if os.path.isdir(download_dir):
            file_paths = list(map(lambda file: os.path.join(download_dir, file), os.listdir(download_dir)))
            ps = PokerSplit(file_paths)
            poker_split_output = ps.run()
            return site_reader_output + poker_split_output
        else:
            log("No files were retrieved. Likely no new games since last run.")
            return []

    def send_groupme_messages(self, messages):
        log("Attempting to send messages...")
        if len(messages) > 0:
            for message in messages:
                log(message, 1)
                if message is not None:
                    text = re.sub(' +', ' ', message)  # GroupMe messages don't format well
                    data = {'bot_id': BOT_ID, 'text': text}
                    # sending post request and saving response as response object
                    r = requests.post(url=API_ENDPOINT, data=data)
                    assert r.ok
                else:
                    log("Message is None, not sending.")
        else:
            log("No message to send")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Files need to be downloaded from Donkhouse
    parser.add_argument('-group_id', default=11395, help="Group ID to get files for")
    parser.add_argument('-output_dir', default="../Output", help="Directory to download files to, relative to script")
    parser.add_argument('-message', default=False, action='store_true', help="Send GroupMe message")
    """ Optional args to control which tables to get results from or where the table output files already exist """
    parser.add_argument('-table_ids', nargs='*', help="Table ids to run results on")
    parser.add_argument('-num_tables', type=int, help="Number of most recent tables to get results from")
    parser.add_argument('-files', nargs='*', help="Files to pull results from")

    args = parser.parse_args()
    log(args)
    banker = zeBanker(args)
    banker.run()
