#!/usr/bin/python3
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
import shutil
from botocore.errorfactory import ClientError

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
epadd_bucket_name = os.getenv("EPADD_BUCKET_NAME")
#What location type is the data stored in (S3 or FS (file system))
epadd_source_type = os.getenv("EPADD_SOURCE_TYPE")
#The prefix or directory of where the data is stored prior to testing
epadd_source_name = os.getenv('EPADD_SOURCE_NAME')
#The prefix that is being monitored for the tests
epadd_int_test_prefix_name = os.getenv('EPADD_TEST_PREFIX_NAME', "")

logging.debug("Executing run_tests.py")

# s3 connection
boto_session = None
s3_resource = None
epadd_bucket = None


def connect_to_buckets():
    '''
        Connect to the ePADD nextcloud s3 buckets
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
                                                                                
                                                                                

def copy_from_source_to_test(dirName = None):
    if dirName is None:
        copy_all_exports()
    else:
        copy_export(dirName)

            
def copy_all_exports():
    '''Copies all exports from the source to the test bucket'''
    for root,dirs,files in os.walk(epadd_source_name):
        for subdir in dirs:
            copy_export(subdir)
            


def copy_export(dirName):
    '''Copies the given export from the source to the test bucket'''
    
    if not os.path.exists(os.path.join(epadd_source_name, dirName)):
        logging.error("{} does not exist in {}.".format(dirName, epadd_source_name))
        raise Exception("{} does not exist in {}.".format(dirName, epadd_source_name))
            
    for root,dirs,files in os.walk(os.path.join(epadd_source_name, dirName)):
        for file in files:
            path = root.replace(epadd_source_name, "")
            path = path.lstrip("/")
            path = os.path.join(epadd_int_test_prefix_name, path)
            logging.debug("From: "+os.path.join(root,file))
            logging.debug("To:"+os.path.join(path,file))
            epadd_bucket.upload_file(os.path.join(root,file),os.path.join(path,file))
        
    #Place the testing drsConfig.txt in the root of the export so it gets picked up first
    epadd_bucket.upload_file(os.path.join(resource_dir, "drsConfig.txt"), os.path.join(epadd_int_test_prefix_name, "drsConfig.txt"))
    