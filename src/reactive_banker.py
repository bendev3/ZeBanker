from ze_banker_groupme import zeBanker
from groupy.client import Client
import argparse
from utils import get_pickle, set_pickle, send_groupme_messages, log
import os

token = ""
#groupme_group_id = "59674981"
groupme_group_id = "59842005"
group_id = 13852
output_dir = "../Output"
message = True

class ReactiveBanker:
    def __init__(self):
        self.client = Client.from_token(token)
        self.groupme_group = self.get_group()
        self.banker = None
        self.new_messages = None
        self.command = ""
        self.commander = None

    def get_group(self):
        for group in self.client.groups.list_all():
            if group.id == groupme_group_id:
                return group

    def get_new_messages(self):
        log("Checking for new messages")
        message_id_list = [msg.id for msg in self.groupme_group.messages.list()]
        messages_pickle = "groupme_messages_{}.pkl".format(groupme_group_id)
        messages_pickle_path = os.path.join(output_dir, messages_pickle)

        if os.path.isfile(messages_pickle_path):
            old_messages = get_pickle(output_dir, messages_pickle)
            messages_to_check = list(set(message_id_list) - set(old_messages))
        else:
            messages_to_check = message_id_list
        set_pickle(message_id_list, output_dir, messages_pickle)
        self.new_messages = set(messages_to_check)

    def get_banker(self):
        log("Checking for a command in new messages")
        for msg in self.groupme_group.messages.list():
            if msg.id in self.new_messages:
                log("New message found {}:{}".format(msg.id, msg.text), 2)
                if "!results" in msg.text:
                    if msg.text == "!results":
                        send_groupme_messages(["Ok {}, getting results from any new tables if they exist.".format(msg.name)])
                        self.banker = zeBanker(None, group_id, output_dir, True, None, None)
                    else:
                        num_tables = int(msg.text.replace("!results", ""))
                        send_groupme_messages(["Ok {}, getting results from the last {} table(s).".format(msg.name, num_tables)])
                        self.banker = zeBanker(None, group_id, output_dir, True, num_tables, None)
                    break

    def run(self):
        self.get_new_messages()
        self.get_banker()

        if self.banker:
            self.banker.run()


if __name__ == "__main__":
    reactive_banker = ReactiveBanker()
    reactive_banker.run()