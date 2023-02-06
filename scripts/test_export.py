#!/usr/bin/python3
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
import shutil

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
test_sidecar_file_path = os.environ.get('TEST_SIDECAR_FILE_PATH')

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


def main(argv):
    # Connect to s3 bucket
    logging.debug("Connect to S3 bucket")
    connect_to_bucket()

    # Place test export in s3
    test_export_filename = test_export_file_path.split('/')[-1]
    epadd_bucket.upload_file(test_export_file_path, test_prefix + test_export_filename)

    # Place drsConfig.txt sidecar file in s3
    if argv[0] != "":
        logging.debug("arguments: " + str(argv))

        # Create empty copy file
        copy_path = os.path.join(os.path.dirname(test_sidecar_file_path), "copy_sidecar.txt")
        logging.debug("copy_path: " + copy_path)

        with open(copy_path, 'w+'): pass

        logging.debug("getting osn line")
        # Get first line (OSN line)
        with open(test_sidecar_file_path, "r") as org_file:
            osn_line = org_file.readline().strip()
            logging.debug("OSN line: " + osn_line)

        with open(copy_path, 'w') as copy_file:
            # Write updated osn to copy file
            copy_file.write(osn_line + argv[0] + "\n")
            logging.debug("New OSN line: " + osn_line + argv[0])

        with open(test_sidecar_file_path, "r") as org_file:
            with open(copy_path, 'w') as copy_file:
                shutil.copyfileobj(org_file, copy_file)

        epadd_bucket.upload_file(copy_path, test_prefix + "drsConfig.txt")
        os.remove(copy_path)

    else:
        epadd_bucket.upload_file(test_sidecar_file_path, test_prefix + "drsConfig.txt")

    # This file triggers the curator app to include a "testing" field in request body to DIMS
    s3_resource.Object(epadd_bucket_name, test_prefix + "TESTTRIGGER").put()

    # For now place manifest since the export manifest is in the zip - since we are going to be switching
    # OPAQUE instead of OPAQUE CONTAINER the exports will no longer be zips and this can be removed
    s3_resource.Object(epadd_bucket_name, test_prefix + "manifest.txt").put()


try:
    main(sys.argv[1:])
    sys.exit(0)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
