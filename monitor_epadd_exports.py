#!/usr/bin/python3

import logging
import os
import re
import sys
import traceback
from datetime import datetime

from requests import exceptions, get, HTTPError

DATEFORMAT = '%Y-%m-%d %H:%M:%S'
relative_dir = os.path.dirname(os.path.realpath(__file__))
logname_template = os.path.dirname(os.path.realpath(__file__)) + "/logs/monitor_epadd_exports_{}.log"
logging.basicConfig(filename=logname_template.format(datetime.today().strftime("%Y%m%d")),
                    format='%(asctime)-2s --%(filename)s-- %(levelname)-8s %(message)s', datefmt=DATEFORMAT,
                    level=logging.DEBUG)

dims_endpoint = os.environ.get('DIMS_ENDPOINT')
dropbox_root_dir = os.environ.get('DROPBOX_PATH')
dropbox_name = os.environ.get('DROPBOX_NAME')

logging.debug("Executing monitor_epadd_exports.py")


def collect_loadreports():
    loadreport_files = []
    loadreport_dir = dropbox_root_dir + "/lts_load_reports" + dropbox_name + "/incoming"
    logging.debug("Checking for load reports in dropbox loc: " + loadreport_dir)

    for root, dirs, files in os.walk(loadreport_dir):
        for name in files:
            if re.match("LOADREPORT", name):
                loadreport_files.append(name)

    return loadreport_files


def notify_dts_loadreports(filename):
    logging.debug("Calling DTS /loadreport for file: " + filename)
    try:
        response = get(dims_endpoint + '/loadreport?filename=' + filename, verify=False)
        logging.debug("Response status code for '/loadreport?filename='" + filename + ": " + str(response.status_code))
        response.raise_for_status()
    except (exceptions.ConnectionError, HTTPError) as e:
        logging.error("Error when calling DTS /loadreport for file: " + str(e))


def collect_failed_batch():
    failed_batch = []
    failed_batch_dir = dropbox_root_dir + dropbox_name + "/incoming"
    logging.debug("Checking failed batches in loc: " + failed_batch_dir)

    for root, dirs, files in os.walk(failed_batch_dir):
        for name in files:
            if re.match("batch.xml.failed", name):
                split_path = root.split("/")
                failed_batch.append(split_path.pop())

    return failed_batch


def notify_dts_failed_batch(batch_name):
    logging.debug("Calling DTS for failed batch: " + batch_name)
    try:
        response = get(dims_endpoint + '/failedBatch?batchName=' + batch_name, verify=False)
        logging.debug("Response status code for '/failedBatch?batchName='" + batch_name + ": " + str(response.status_code))
        response.raise_for_status()
    except (exceptions.ConnectionError, HTTPError) as e:
        logging.error("Error when calling DTS /loadreport for file: " + str(e))


def main():
    # Collect successful ingests
    loadreport_list = collect_loadreports()
    logging.debug("Load report files returned: " + str(loadreport_list))
    for loadreport in loadreport_list:
        notify_dts_loadreports(loadreport)

    # Collect failed ingests
    failed_batch_list = collect_failed_batch()
    logging.debug("Failed batch files returned: " + str(failed_batch_list))
    for failed_batch in failed_batch_list:
        notify_dts_failed_batch(failed_batch)


try:
    main()
    sys.exit(0)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
