#!/usr/bin/python3
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
import shutil

import boto3

aws_access_key = os.getenv('NEXTCLOUD_AWS_ACCESS_KEY')
aws_secret_key = os.getenv('NEXTCLOUD_AWS_SECRET_KEY')
resource_dir = os.getenv("DATA_PATH")
#The location of where the data is stored prior to testing
epadd_source_bucket_name = os.getenv('EPADD_SOURCE_BUCKET_NAME')
#The bucket that is being monitored for the tests
epadd_test_bucket_name = os.getenv('EPADD_TEST_BUCKET_NAME')
test_prefix = os.getenv('TEST_PREFIX', "")

test_export_file_path = os.getenv('TEST_EXPORT_FILE_PATH')
test_sidecar_file_path = os.getenv('TEST_SIDECAR_FILE_PATH')

logging.debug("Executing test_export.py")

# s3 connection
boto_session = None
s3_resource = None
epadd_source_bucket = None
epadd_test_bucket = None


def connect_to_buckets():
    '''
        Connect to the ePADD nextcloud s3 buckets
    '''
    global boto_session
    global s3_resource
    global epadd_source_bucket
    global epadd_test_bucket

    boto_session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key)

    # Then use the session to get the resource
    s3_resource = boto_session.resource('s3')

    epadd_source_bucket = s3_resource.Bucket(epadd_source_bucket_name)
    logging.debug("Connected to S3 source bucket: " + epadd_source_bucket_name)
    
    epadd_test_bucket = s3_resource.Bucket(epadd_test_bucket_name)
    logging.debug("Connected to S3 test bucket: " + epadd_test_bucket_name)

def copy_from_source_to_test(dirName = None):
    if dirName is None:
        copy_all_exports()
    else:
        copy_export(dirName)

            
def copy_all_exports():
    '''Copies all exports from the source bucket to the test bucket'''
    for obj in epadd_source_bucket.objects.all():
        copy_export(obj.key)


def copy_export(dirName):
    '''Copies the given export from the source bucket to the test bucket'''
    #Copy the dir
    for obj in epadd_source_bucket.objects.filter(Prefix=dirName):
        source = { 'Bucket': epadd_source_bucket,
                   'Key': obj.key}
        # replace the prefix
        new_obj = epadd_test_bucket.Object(obj.key)
        new_obj.copy(old_source)
        
    #Place the testing drsConfig.txt in the root of the export so it gets picked up first
    epadd_teest_bucket.upload_file(os.path.join(resource_dir, "drsConfig.txt.template"), os.path.join(test_prefix, dirName, "drsConfig.txt"))
    