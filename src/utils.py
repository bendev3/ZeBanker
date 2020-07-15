import os
import pickle
import re
import requests
import datetime

LOGLEVEL = 2
API_ENDPOINT = "https://api.groupme.com/v3/bots/post"


def log(msg, level=0):
    if level <= LOGLEVEL:
        print(datetime.datetime.now(), msg)


def val_to_float(val):
    return 0 if val == '' else float(val)


def get_pickle(output_dir, name):
    file_path = os.path.join(output_dir, name)
    return pickle.load(open(file_path, "rb"))


def set_pickle(object, output_dir, name):
    file_path = os.path.join(output_dir, name)
    pickle.dump(object, open(file_path, "wb"))


def send_groupme_messages(messages, bot_id, send_message=False):
    log("Attempting to send message, send_message: {}".format(send_message))
    if len(messages) > 0:
        for message in messages:
            if message is not None:
                if send_message:
                    log(message, 1)
                    text = re.sub(' +', ' ', message)  # GroupMe messages don't format well
                    data = {'bot_id': bot_id, 'text': text}
                    # sending post request and saving response as response object
                    r = requests.post(url=API_ENDPOINT, data=data)
                    assert r.ok
                else:
                    print(message)
            else:
                log("Message is None, not sending.")
    else:
        log("No message to send")


def duplicate_at_start(l):
    for i in range(len(l)):
        if i > 2:
            if l[:i] == l[i:2*i]:
                print("Duplicate {} at start".format(l[:i]))
                return True
    return False


def is_int(val):
    try:
        num = int(val)
    except ValueError:
        return False
    return True