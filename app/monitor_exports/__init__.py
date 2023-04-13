#!/usr/bin/python3
import logging
import os, os.path, glob, shutil
import re
import sys
import traceback
from datetime import datetime, timedelta
import jwt
import hashlib
import jcs

import boto3

import requests
from requests import exceptions, HTTPError
import py7zr

DATEFORMAT = '%Y-%m-%d %H:%M:%S'
log_dir = os.getenv("LOG_DIR", "/home/appuser/epadd-curator-app/logs")
log_level = os.getenv("LOG_LEVEL", "WARNING")
logname_template = os.path.join(log_dir, "monitor_epadd_exports_{}.log")
logging.basicConfig(filename=logname_template.format(datetime.today().strftime("%Y%m%d")),
                    format='%(asctime)-2s --%(filename)s-- %(levelname)-8s %(message)s', datefmt=DATEFORMAT,
                    level=log_level)

#Prevents S3 gem from logging too much
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

dims_endpoint = os.getenv('DIMS_ENDPOINT')
aws_access_key = os.getenv('NEXTCLOUD_AWS_ACCESS_KEY')
aws_secret_key = os.getenv('NEXTCLOUD_AWS_SECRET_KEY')
epadd_bucket_name = os.getenv('EPADD_BUCKET_NAME')
epadd_dropbox_prefix_name = os.getenv("EPADD_DROPBOX_PREFIX_NAME", "")
jwt_private_key_path = os.getenv('JWT_PRIVATE_KEY_PATH')
jwt_expiration = int(os.getenv('JWT_EXPIRATION'))
zip_path = os.getenv('ZIPPED_EXPORT_PATH')
download_export_path = os.getenv('DOWNLOAD_EXPORT_PATH')
environment = os.getenv("ENV")

logging.debug("Executing monitor_epadd_exports.py")

# s3 connection
boto_session = None
s3_resource = None
epadd_bucket = None


def call_dims_ingest(manifest_object_key):
    """
        This function generates the jwt token to call DIMS with. Once ingest is successfully
        called, an ingest.txt is placed in the export dir. If the ingest call fails, an ingest.txt.failed
        file is placed in the export dir.
    """
    logging.debug("Preparing to call DIMS")
    # get parent prefix of manifest file
    manifest_parent_prefix = os.path.dirname(manifest_object_key)

    try:
        with open(jwt_private_key_path) as jwt_private_key_file:
            jwt_private_key = jwt_private_key_file.read()
    except:
        logging.error("Error opening private jwt token at path: " + jwt_private_key_path)

    
    download_dir = retrieve_export(download_export_path, manifest_parent_prefix)
    
    payload_data = construct_payload_body(download_dir, manifest_parent_prefix)

    logging.debug("Payload data extracted for {}".format(manifest_object_key))

    # 7zip up directory
    zip_file = zip_export(zip_path, download_dir)
    if not zip_file:
        raise Exception("{} did not zip properly to {}".format(download_dir, zip_path))

    # delete contents of s3 export folder
    try:
        logging.debug("Deleting s3 export folder {}".format(manifest_parent_prefix))
        epadd_bucket.objects.filter(Prefix=manifest_parent_prefix).delete()
    except:
        logging.error("Error while deleting original export from S3 folder: " + manifest_parent_prefix)

    # upload zip file back to manifest directory (manifest_parent_prefix)
    upload_zip_export(zip_file, manifest_parent_prefix)

    # delete downloaded export and zip export
    try:
        os.remove(zip_file)
    except:
        logging.error("Error while deleting zipped export: " + zip_file)
    try:
        shutil.rmtree(download_dir)
    except:
        logging.error("Error while deleting download directory: " + download_dir)
        
    # calculate iat and exp values
    current_datetime = datetime.now()
    current_epoch = int(current_datetime.timestamp())
    expiration = current_datetime + timedelta(seconds=jwt_expiration)

    # get request_body hash
    request_body = jcs.canonicalize(payload_data).decode()
    bodySHA256Hash = hashlib.sha256(request_body.encode()).hexdigest()

    logging.debug("Generating JWT Token")
    # generate JWT token
    jwt_token = jwt.encode(
        payload={'iss': 'ePADD', 'iat': current_epoch, 'exp': int(expiration.timestamp()),
                 'bodySHA256Hash': bodySHA256Hash},
        key=jwt_private_key,
        algorithm='RS256',
        headers={"alg": "RS256", "typ": "JWT", "kid": "defaultEpadd"}
    )

    headers = {"Authorization": "Bearer " + jwt_token}

    logging.debug("Calling ingest at: " + dims_endpoint + "/ingest " + "with request body: " + str(payload_data))

    # Call DIMS ingest
    ingest_epadd_export = None
    try:
        ingest_epadd_export = requests.post(
            dims_endpoint + '/ingest',
            headers=headers,
            json=payload_data,
            verify=False)
    except (exceptions.ConnectionError, HTTPError) as e:
        logging.error("Error when calling DIMS /ingest: " + str(e))

    json_ingest_response = ingest_epadd_export.json()
    logging.debug(json_ingest_response)

    # Put file to indicate ingest status of export
    if json_ingest_response["status"] == "failure":
        logging.debug("Putting ingest.txt.failed at prefix: " + manifest_parent_prefix)
        content = ""
        s3_resource.Object(epadd_bucket_name, os.path.join(manifest_parent_prefix, "ingest.txt.failed")).put(Body=content)
    else:
        logging.debug("Putting ingest.txt at prefix: " + manifest_parent_prefix)
        content = "Pending ingest.."
        s3_resource.Object(epadd_bucket_name, os.path.join(manifest_parent_prefix, "ingest.txt")).put(Body=content)

    # Remove loading file
    s3_resource.Object(epadd_bucket_name, os.path.join(manifest_parent_prefix, "LOADING")).delete()


def construct_payload_body(download_dir, full_prefix):
    """
        Construct the request body with appropriate metadata. A "testing" field is added
        if a TESTTRIGGER file exists in the export
    """
    logging.debug("Constructing request body")
    
    drsconfig = None
    drsconfig_list = glob.glob(os.path.join(download_dir, "**", "drsConfig.txt") ,recursive = True)
                               
    if drsconfig_list:
        drsconfig = drsconfig_list[0]
    else:
        raise Exception("drsConfig.txt not found in export {}".format(download_dir))
        
        
    logging.debug("Retrieved sidecar metadata from " + drsconfig)

    metadata_dict = {}
    with open(drsconfig) as drs_config_file:
        for line in drs_config_file:
            #Remove unicode and whitespace
            line = strip_unicode_and_whitespace(line)
            if len(line) > 0:
                split_val = line.split('=')
                metadata_dict[split_val[0]] = split_val[1]
    logging.debug("Metadata dictionary: " + str(metadata_dict))

    if metadata_dict["ownerSuppliedName"].strip() == "":
        logging.warn("ownerSuppliedName was not provided in drsConfig.txt for {}".format(os.path.basename(download_dir)))
        unique_osn = "osn_" + str(int(datetime.now().timestamp()))
    else:
        unique_osn = metadata_dict["ownerSuppliedName"].strip()

    payload_data = {"package_id": unique_osn,
                    "s3_path": full_prefix,
                    "s3_bucket_name": epadd_bucket_name,
                    "admin_metadata": {
                        "accessFlag": metadata_dict["accessFlag"],
                        "contentModel": metadata_dict["contentModel"],
                        "depositingSystem": metadata_dict["depositingSystem"],
                        "firstGenerationInDrs": metadata_dict["firstGenerationInDrs"],
                        "objectRole": metadata_dict["objectRole"],
                        "usageClass": metadata_dict["usageClass"],
                        "storageClass": metadata_dict["storageClass"],
                        "ownerCode": metadata_dict["ownerCode"],
                        "billingCode": metadata_dict["billingCode"],
                        "resourceNamePattern": metadata_dict["resourceNamePattern"],
                        "urnAuthorityPath": metadata_dict["urnAuthorityPath"],
                        "depositAgent": metadata_dict["depositAgent"],
                        "depositAgentEmail": metadata_dict["depositAgentEmail"],
                        "successEmail": metadata_dict["successEmail"],
                        "failureEmail": metadata_dict["failureEmail"],
                        "successMethod": metadata_dict["successMethod"],
                        "adminCategory": metadata_dict["adminCategory"],
                        "embargoBasis": metadata_dict["embargoBasis"],
                        "original_queue": "/queue/transfer_ready",
                        "retry_count": 1
                    }
                    }

    return payload_data

def strip_unicode_and_whitespace(line):
    #Remove whitespace
    line = line.strip()
    #Remove null bytes
    line = line.replace("\x00",'') 
    #Remove unicode
    line = line.encode("ascii", "ignore").decode()
    return line
            

def key_exists(key):
    """
        Determine if the given key exists
    """
    epadd_bucket_objects = epadd_bucket.objects.all()
    return any([obj.key == key for obj in epadd_bucket_objects])


def connect_to_bucket():
    """
        Connect to the ePADD nextcloud s3 bucket
    """
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


def collect_exports():
    """
        In the ePADD nextcloud bucket, look for a manifest.txt, manifest-md5.txt or manifest-sha256.txt.
        Once found, ensure there is no ingest.txt or ingest.txt.failed file, which indicate ingest has
        already been called on that export.
    """
    manifest_object_keys = []

    logging.debug("Search for manifest-<algorithm>.txt file in bucket/prefix: " + os.path.join(epadd_bucket_name, epadd_dropbox_prefix_name))

    epadd_bucket_objects = []
    #Format is <prefix>/<user 'dropbox' name>/<export name>/<data>
    #Example dropboxes/lts-test/ePADD-eml-export/....
    if epadd_dropbox_prefix_name:
        dropbox_name = epadd_dropbox_prefix_name
        if "/" not in dropbox_name:
            dropbox_name += "/" 
        #This helps retrieve the user dropboxes
        user_dropboxes = s3_resource.meta.client.list_objects_v2(Bucket=epadd_bucket_name, Prefix=dropbox_name, Delimiter="/")
        
        for user_dropbox in user_dropboxes.get('CommonPrefixes'):
            user_dropbox_path = user_dropbox.get('Prefix')
            #This gets the list of the exported names under the user 'dropbox'
            export_names = s3_resource.meta.client.list_objects_v2(Bucket=epadd_bucket_name, Prefix=user_dropbox_path, Delimiter="/")
            if "CommonPrefixes" in export_names:
                for export_dir in export_names.get('CommonPrefixes'):
                    epadd_bucket_objects.append(export_dir.get('Prefix'))
    #Format is just <export name>/<data>
    #Example ePADD-eml-export/<data>
    else:   
        #This gets the list of the exported names under the bucket
        export_names = s3_resource.meta.client.list_objects_v2(Bucket=epadd_bucket_name, Delimiter="/")
        for export_dir in export_names.get('CommonPrefixes'):
            epadd_bucket_objects.append(export_dir.get('Prefix'))

    for epadd_bucket_object in epadd_bucket_objects:
        #skip user dir
        if re.search('^user[/]?', epadd_bucket_object, re.IGNORECASE):
            logging.debug("Skipping user dir: {}".format(epadd_bucket_object))
            pass
        else:
            objects = epadd_bucket.objects.filter(Prefix=epadd_bucket_object)
            for obj in objects:
                if re.search('manifest(-md5|-sha256)?.txt', obj.key, re.IGNORECASE):
                    logging.debug("Manifest found: {}".format(obj.key))
                    manifest_parent_prefix = os.path.dirname(obj.key)
                    if not (key_exists(os.path.join(manifest_parent_prefix, "ingest.txt"))
                            or key_exists(os.path.join(manifest_parent_prefix, "ingest.txt.failed"))
                            or key_exists(os.path.join(manifest_parent_prefix,"LOADING"))):
                        logging.debug("Putting LOADING file at prefix: " + manifest_parent_prefix)
                        s3_resource.Object(epadd_bucket_name, os.path.join(manifest_parent_prefix, "LOADING")).put(Body="")
                        manifest_object_keys.append(obj.key)
                        logging.debug("Object key added: " + obj.key)
                    break

    return manifest_object_keys


def retrieve_export(download_path, manifest_parent_prefix):
    """
        pull down the export to local storage prior to zip (7zip)
    """
    try:
        logging.debug("Downloading {}".format(manifest_parent_prefix))
        for obj in epadd_bucket.objects.filter(Prefix=manifest_parent_prefix):
            
            #Remove dropbox
            keywithoutdropboxprefix = obj.key[len(epadd_dropbox_prefix_name):]
            keywithoutdropboxprefix = keywithoutdropboxprefix.lstrip("/")
            logging.debug("without dropbox: {}".format(keywithoutdropboxprefix))
            if environment == "development":
                key = obj.key
            else:
                userbucket = keywithoutdropboxprefix[0:keywithoutdropboxprefix.find("/")]
                logging.debug("user bucket: {}".format(userbucket))
                key = keywithoutdropboxprefix[len(userbucket):]
                key = key.lstrip("/")

            logging.debug("Moving {}".format(key))

            local_file = os.path.join(download_path, key)
            # If the obj.key is a path, and the corresponding download dir doesn't exist
            # then create the dir and don't attempt to download a file.
            # Hidden files also have obj.key ending in '/' and will be excluded from download.
            if (obj.key[-1] == "/"):
                if not os.path.exists(local_file):
                    os.makedirs(local_file)
                    logging.debug("Created dir {}".format(local_file))
                continue
            
            # Else if obj.key is a file, create the dir if the download dir doesn't already
            # exist. Then attempt to download the file.
            elif not os.path.exists(os.path.dirname(local_file)):
                os.makedirs(os.path.dirname(local_file))
                logging.debug("Created dir for file {}".format(local_file))
            epadd_bucket.download_file(obj.key, local_file)

        pathwithoutdropboxprefix = manifest_parent_prefix[len(epadd_dropbox_prefix_name):]
        pathwithoutdropboxprefix = pathwithoutdropboxprefix.lstrip("/")
        logging.debug("without dropbox: {}".format(pathwithoutdropboxprefix))
        if environment == "development":
            download_dir = manifest_parent_prefix
        else:
            userbucket = pathwithoutdropboxprefix[0:pathwithoutdropboxprefix.find("/")]    
            download_dir = pathwithoutdropboxprefix[len(userbucket):]
            download_dir = download_dir.lstrip("/")

        download_local_dir = os.path.join(download_path, download_dir)
        return download_local_dir
    except Exception as err:
        logging.error(traceback.format_exc())
        raise err


def zip_export(zip_path, directory_to_zip):
    """
        zip up export in 7zip format
    """
    try:
        manifest_parent_prefix = os.path.basename(directory_to_zip)
        zip_filename = os.path.join(zip_path, manifest_parent_prefix + ".7z")
        logging.debug("Zipping directory {} into {} ".format(directory_to_zip, zip_filename))
        with py7zr.SevenZipFile(zip_filename, 'w') as archive:
            archive.writeall(directory_to_zip, manifest_parent_prefix)
        return zip_filename
    except Exception as err:
        logging.error(traceback.format_exc())
        logging.error("Error zipping up export: " + manifest_parent_prefix)
        logging.error(err)
        return False


def upload_zip_export(zip_path, manifest_parent_prefix):
    """
        upload zipped export back to s3
    """
    try:
        zip_file = os.path.basename(zip_path)
        epadd_bucket.upload_file(zip_path, os.path.join(manifest_parent_prefix, zip_file))
        return True
    except:
        logging.error(traceback.format_exc())
        logging.error("Error uploading zip archive: " + zip_path)
        return False


