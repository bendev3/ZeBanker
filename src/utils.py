
LOGLEVEL = 2


def log(msg, level=0):
    if level <= LOGLEVEL:
        print(msg)


def val_to_float(val):
    return 0 if val == '' else float(val)


#  Not in use, leaving for now
"""
import os
from google.cloud import storage

BUCKET_NAME = "ze_banker"

def upload_blob(source_file_name, destination_blob_name):
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"
    log("Uploading {} to google cloud as {}".format(source_file_name, destination_blob_name), 1)
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)


def download_blob(source_blob_name, destination_file_name):
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"
    log("Downloading {} from google cloud to {}".format(source_blob_name, destination_file_name), 1)
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
"""