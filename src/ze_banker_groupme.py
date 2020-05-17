from poker_split import PokerSplit
from site_reader import SiteReader
from datetime import datetime
import requests
from utils import log
import os
import argparse

BOT_ID = "52ffe9618e4c11409b9b0bb089"
API_ENDPOINT = "https://api.groupme.com/v3/bots/post"
GROUP_ID = 11395
NUM_TABLES = None

class zeBanker:
    def __init__(self, arguments):
        self.files = arguments.files
        self.group_id = arguments.group_id
        self.num_tables = arguments.num_tables
        self.output_dir = arguments.output_dir

    def run(self):
        if self.files:
            log("files argument provided, running on existing files")
            msgs = banker.run_local()
        else:
            log("files argument not provided, retrieving files from Donkhouse")
            msgs = banker.run_external()
        self.send_groupme_message(msgs)

    def run_local(self):
        ps = PokerSplit(self.files)
        return ps.run()

    def run_external(self):
        log("Attempting to get results from Donkhouse")
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            script_path = os.path.dirname(os.path.abspath(__file__))
            download_dir = os.path.abspath(os.path.join(*[script_path, self.output_dir, timestamp]))
            site_reader = SiteReader(self.group_id, self.num_tables, download_dir)
            site_reader.run()
            if os.path.isdir(download_dir):
                file_paths = list(map(lambda file: os.path.join(download_dir, file), os.listdir(download_dir)))
                ps = PokerSplit(file_paths)
                return ps.run()
            else:
                log("No files were retrieved. Likely no new games since last run.")
                return None
        except Exception as e:
            msgs = ["Error occurred retrieving results:{}".format(e)]
            log(msgs)
            return msgs

    def send_groupme_message(self, messages):
        if len(messages) > 0:
            for message in messages:
                log("Attempting to send message...\n{}".format(message))
                if message is not None:
                    data = {'bot_id': BOT_ID, 'text': message}
                    # sending post request and saving response as response object
                    try:
                        requests.post(url=API_ENDPOINT, data=data)
                    except Exception as e:
                        log("Could not send GroupmeMesage, error:{}".format(e))
                else:
                    log("Message is None, not sending.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Files provided
    parser.add_argument('-files', nargs='*', help="Files to pull results from")

    # Files need to be downloaded from Donkhouse
    parser.add_argument('-group_id', default=11395, help="Group ID to get files for")
    # If provided, will retrieve only the num_tables number of recent tables.
    # Otherwise, all the tables since the last backup will be retrieved
    parser.add_argument('-num_tables', type=int, help="Number of most recent tables to get results from")
    parser.add_argument('-output_dir', default="../../Output", help="Directory to download files to, relative to script")
    args = parser.parse_args()

    log(args)
    banker = zeBanker(args)
    banker.run()
