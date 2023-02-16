#!/usr/bin/python3
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
import shutil

import boto3

DATEFORMAT = '%Y-%m-%d %H:%M:%S'
log_dir = os.getenv("LOG_DIR", "/home/appuser/epadd-curator-app/logs")
log_level = os.getenv("LOG_LEVEL", "WARNING")
logname_template = os.path.join(log_dir, "run_tests_{}.log")
logging.basicConfig(filename=logname_template.format(datetime.today().strftime("%Y%m%d")),
                    format='%(asctime)-2s --%(filename)s-- %(levelname)-8s %(message)s', datefmt=DATEFORMAT,
                    level=log_level)

#Prevents S3 gem from logging too much
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

aws_access_key = os.getenv('NEXTCLOUD_AWS_ACCESS_KEY')
aws_secret_key = os.getenv('NEXTCLOUD_AWS_SECRET_KEY')
resource_dir = os.getenv("DATA_PATH")
#What location type is the data stored in (S3 or FS (file system))
epadd_source_type = os.getenv("EPADD_SOURCE_TYPE")
#The location of where the data is stored prior to testing
epadd_source_name = os.getenv('EPADD_SOURCE_NAME')
#The bucket that is being monitored for the tests
epadd_test_bucket_name = os.getenv('EPADD_TEST_BUCKET_NAME')
test_prefix = os.getenv('TEST_PREFIX', "")

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

    if epadd_source_type == "S3":
        epadd_source_bucket = s3_resource.Bucket(epadd_source_name)
        logging.debug("Connected to S3 source bucket: " + epadd_source_name)
    
    epadd_test_bucket = s3_resource.Bucket(epadd_test_bucket_name)
    logging.debug("Connected to S3 test bucket: " + epadd_test_bucket_name)

def copy_from_source_to_test(dirName = None):
    if dirName is None:
        copy_all_exports()
    else:
        copy_export(dirName)

            
def copy_all_exports():
    '''Copies all exports from the source to the test bucket'''
    if epadd_source_type == "S3":
        result = s3_resource.meta.client.list_objects(Bucket=epadd_source_bucket, Delimiter='/')
        for obj in result.get('CommonPrefixes'):
            copy_export(obj.get('Prefix'))
    else:
        for root,dirs,files in os.walk(epadd_source_name):
            for subdir in dirs:
                copy_export(subdir)
            


def copy_export(dirName):
    '''Copies the given export from the source to the test bucket'''
    logging.debug("Copying export "+dirName + " from " + epadd_source_name)
    if epadd_source_type == "S3":
        #Copy the dir
        for obj in epadd_source_bucket.objects.filter(Prefix=dirName):
            source = { 'Bucket': epadd_source_bucket,
                       'Key': obj.key}
            # replace the prefix
            new_obj = epadd_test_bucket.Object(os.path.join(test_prefix, obj.key))
            new_obj.copy(source)
    else:
        for root,dirs,files in os.walk(os.path.join(epadd_source_name, dirName)):
            for file in files:
                path = root.replace(epadd_source_name, "")
                path = path.lstrip("/")
                logging.debug("path: " + path)
                logging.debug("Uploading {} to {}".format(os.path.join(root, file), os.path.join(test_prefix, path, file)))
                epadd_test_bucket.upload_file(os.path.join(root,file),os.path.join(test_prefix,path,file))
        
    #Place the testing drsConfig.txt in the root of the export so it gets picked up first
    epadd_test_bucket.upload_file(os.path.join(resource_dir, "drsConfig.txt.template"), os.path.join(test_prefix, dirName, "drsConfig.txt"))
    