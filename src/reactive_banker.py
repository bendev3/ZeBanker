from ze_banker_groupme import zeBanker
from groupy.client import Client
import argparse
from utils import get_pickle, set_pickle, send_groupme_messages, log, is_int
import os
import configparser
import time

script_path = os.path.dirname(os.path.abspath(__file__))

class ReactiveBanker:
    def __init__(self, cfg):
        self.token = cfg["ZeBanker"]["token"]
        self.groupme_group_id = cfg["ZeBanker"]["groupme_group_id"]
        self.donk_group_id = cfg["ZeBanker"]["donk_group_id"]
        self.output_dir = os.path.join(script_path, cfg["ZeBanker"]["output_dir_relative_to_script"])
        self.message = cfg["ZeBanker"]["message"] == "True"
        self.bot_id = cfg["ZeBanker"]["bot_id"]

        self.client = Client.from_token(self.token)
        self.groupme_group = self.get_group()
        self.banker = None
        self.new_messages = None
        self.command = ""
        self.commander = None

    def init_run(self):
        self.banker = None
        self.new_messages = None
        self.command = ""
        self.commander = None

    def get_group(self):
        for group in self.client.groups.list_all():
            if group.id == self.groupme_group_id:
                return group

    def get_new_messages(self):
        log("Checking for new messages", 3)
        message_id_list = [msg.id for msg in self.groupme_group.messages.list()]
        messages_pickle = "groupme_messages_{}.pkl".format(self.groupme_group_id)
        messages_pickle_path = os.path.join(self.output_dir, messages_pickle)

        if os.path.isfile(messages_pickle_path):
            old_messages = get_pickle(self.output_dir, messages_pickle)
            messages_to_check = list(set(message_id_list) - set(old_messages))
        else:
            messages_to_check = message_id_list
        set_pickle(message_id_list, self.output_dir, messages_pickle)
        self.new_messages = set(messages_to_check)

    def get_banker(self):
        log("Parsing messages and potentially constructing zeBanker object", 3)
        for msg in self.groupme_group.messages.list():
            if msg.id in self.new_messages:
                log("New message found {}:{}".format(msg.id, msg.text), 2)
                if "!results" in msg.text:
                    if msg.text.strip() == "!results":
                        send_groupme_messages(["Ok {}, getting results from any new tables since the last run.".format(msg.name)], self.bot_id, self.message)
                        self.banker = zeBanker(None, self.donk_group_id, self.output_dir, self.message, None, None, self.bot_id)
                    elif is_int(msg.text.replace("!results", "")):
                        num_tables = int(msg.text.replace("!results", ""))
                        send_groupme_messages(["Ok {}, getting results from the last {} table(s).".format(msg.name, num_tables)], self.bot_id, self.message)
                        self.banker = zeBanker(None, self.donk_group_id, self.output_dir, self.message, num_tables, None, self.bot_id)
                    break

    def run(self):
        try:
            self.init_run()
            self.get_new_messages()
            self.get_banker()

            if self.banker:
                self.banker.run()
        except AssertionError as e:
            send_groupme_messages(["Error: {}".format(str(e))], self.bot_id, self.message)
            log("Exception occurred in reactive_banker.run(): {}".format(str(e)))
        except Exception as e:
            log("Exception occurred in reactive_banker.run(): {}".format(str(e)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', help="Config file")
    args = parser.parse_args()
    cfg = configparser.ConfigParser()
    cfg.read(args.c)

    log("Running with config {}".format(args.c))
    reactive_banker = ReactiveBanker(cfg)

    while True:
        reactive_banker.run()
        time.sleep(1.0)

