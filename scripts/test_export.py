#!/usr/bin/python3
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta

import boto3


DATEFORMAT = '%Y-%m-%d %H:%M:%S'
relative_dir = os.path.dirname(os.path.realpath(__file__))
logname_template = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/logs/test_export_{}.log"
logging.basicConfig(filename=logname_template.format(datetime.today().strftime("%Y%m%d")),
                    format='%(asctime)-2s --%(filename)s-- %(levelname)-8s %(message)s', datefmt=DATEFORMAT,
                    level=logging.DEBUG)

aws_access_key = os.environ.get('NEXTCLOUD_AWS_ACCESS_KEY')
aws_secret_key = os.environ.get('NEXTCLOUD_AWS_SECRET_KEY')
epadd_bucket_name = os.environ.get('EPADD_BUCKET_NAME')
test_export_file_path = os.environ.get('TEST_EXPORT_FILE_PATH')
test_prefix = os.environ.get('TEST_PREFIX')

logging.debug("Executing test_export.py")

# s3 connection
boto_session = None
s3_resource = None
epadd_bucket = None


def connect_to_bucket():
    '''
        Connect to the ePADD nextcloud s3 bucket
    '''
    global boto_session
    global s3_resource
    global epadd_bucket

    boto_session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key)

    # Then use the session to get the resource
    s3_resource = boto_session.resource('s3')

    epadd_bucket = s3_resource.Bucket(epadd_bucket_name)
    logging.debug("Connected to S3 bucket: " + epadd_bucket_name)


def main():
    # Connect to s3 bucket
    logging.debug("Connect to S3 bucket")
    connect_to_bucket()

    # Place test export in s3
    test_export_filename = test_export_file_path.split('/')[-1]
    epadd_bucket.upload_file(test_export_file_path, test_prefix + test_export_filename)

    # Place drsConfig.txt sidecar file in s3
    epadd_bucket.upload_file("/home/appuser/epadd-curator-app/resources/drsConfig.txt", test_prefix + "drsConfig.txt")

    # This file triggers the curator app to include a "testing" field in request body to DIMS
    s3_resource.Object(epadd_bucket_name, test_prefix + "TESTTRIGGER").put()

    # For now place manifest since the export manifest is in the zip - since we are going to be switching
    # OPAQUE instead of OPAQUE CONTAINER the exports will no longer be zips and this can be removed
    s3_resource.Object(epadd_bucket_name, test_prefix + "manifest.txt").put()


try:
    main()
    sys.exit(0)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
