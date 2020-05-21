import os
import pickle
import re
import requests

# Legit
BOT_ID = "e4808a5a0d7f8fd6ec06fe42bc"
# Test
#BOT_ID = "89997e88121f3d04ed8f9a7a2f"
API_ENDPOINT = "https://api.groupme.com/v3/bots/post"

LOGLEVEL = 2


def log(msg, level=0):
    if level <= LOGLEVEL:
        print(msg)


def val_to_float(val):
    return 0 if val == '' else float(val)


def get_pickle(output_dir, name):
    file_path = os.path.join(output_dir, name)
    return pickle.load(open(file_path, "rb"))


def set_pickle(object, output_dir, name):
    file_path = os.path.join(output_dir, name)
    pickle.dump(object, open(file_path, "wb"))


def send_groupme_messages(messages):
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
