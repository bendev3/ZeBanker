from poker_split import PokerSplit
from site_reader import SiteReader
from datetime import datetime
from utils import log, send_groupme_messages
import os
import argparse
import time

class zeBanker:
    def __init__(self, files, group_id, output_dir, message, num_tables, table_ids, bot_id, nets = None):
        self.files = files
        self.group_id = group_id
        self.output_dir = output_dir
        self.message = message
        self.num_tables = num_tables
        self.table_ids = table_ids
        self.bot_id = bot_id
        self.nets = nets

    def run(self):
        if self.files:
            log("files argument provided, running on existing files")
            msgs = self.run_local()
        elif self.nets:
            msgs = self.run_with_nets()
        else:
            log("files argument not provided, retrieving files from Donkhouse")
            msgs = self.run_external()

        send_groupme_messages(msgs, self.bot_id, self.message)


    def run_local(self):
        ps = PokerSplit(self.files)
        return ps.run()

    def run_with_nets(self):
        ps = PokerSplit(None, nets=self.nets)
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
            send_groupme_messages(["No files retrieved. Likely no new games since last run."], self.bot_id, self.message)
            log("No files were retrieved. Likely no new games since last run.")
            return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Files need to be downloaded from Donkhouse
    parser.add_argument('-group_id', default=11395, help="Group ID to get files for")
    parser.add_argument('-output_dir', default="../Output", help="Directory to download files to, relative to script")
    parser.add_argument('-message', default=False, action='store_true', help="Send GroupMe message")
    parser.add_argument('-bot_id', help="GroupMe ID")

    """ Optional args to control which tables to get results from or where the table output files already exist """
    parser.add_argument('-table_ids', nargs='*', help="Table ids to run results on")
    parser.add_argument('-num_tables', type=int, help="Number of most recent tables to get results from")
    parser.add_argument('-files', nargs='*', help="Files to pull results from")


    args = parser.parse_args()
    log(args)
    banker = zeBanker(args.files, args.group_id, args.output_dir, args.message, args.num_tables, args.table_ids, args.bot_id)
    banker.run()
