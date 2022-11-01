#!/usr/bin/python3
import logging
import os
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

DATEFORMAT = '%Y-%m-%d %H:%M:%S'
relative_dir = os.path.dirname(os.path.realpath(__file__))
logname_template = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/logs/monitor_epadd_exports_{}.log"
logging.basicConfig(filename=logname_template.format(datetime.today().strftime("%Y%m%d")),
                    format='%(asctime)-2s --%(filename)s-- %(levelname)-8s %(message)s', datefmt=DATEFORMAT,
                    level=logging.DEBUG)

dims_endpoint = os.environ.get('DIMS_ENDPOINT')
aws_access_key = os.environ.get('NEXTCLOUD_AWS_ACCESS_KEY')
aws_secret_key = os.environ.get('NEXTCLOUD_AWS_SECRET_KEY')
epadd_bucket_name = os.environ.get('EPADD_BUCKET_NAME')
jwt_private_key_path = os.environ.get('JWT_PRIVATE_KEY_PATH')
jwt_expiration = int(os.environ.get('JWT_EXPIRATION'))

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
    manifest_parent_prefix = get_parent_prefix(manifest_object_key)

    try:
        with open(jwt_private_key_path) as jwt_private_key_file:
            jwt_private_key = jwt_private_key_file.read()
    except:
        logging.error("Error opening private jwt token at path: " + jwt_private_key_path)

    payload_data = construct_payload_body(manifest_object_key)

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
        s3_resource.Object(epadd_bucket_name, manifest_parent_prefix + "ingest.txt.failed").put(Body=content)
    else:
        logging.debug("Putting ingest.txt at prefix: " + manifest_parent_prefix)
        content = "Pending ingest.."
        s3_resource.Object(epadd_bucket_name, manifest_parent_prefix + "ingest.txt").put(Body=content)

    # Remove loading file
    s3_resource.Object(epadd_bucket_name, manifest_parent_prefix + "LOADING").delete()


def construct_payload_body(manifest_object_key):
    """
        Construct the request body with appropriate metadata. A "testing" field is added
        if a TESTTRIGGER file exists in the export
    """
    logging.debug("Constructing request body")
    # get parent prefix of manifest file
    manifest_parent_prefix = get_parent_prefix(manifest_object_key)

    # get contents of drsConfig.txt
    obj = s3_resource.Object(epadd_bucket_name, manifest_parent_prefix + "drsConfig.txt")
    data = obj.get()['Body'].read().decode('utf-8')
    logging.debug("Retrieved sidecar metadata from " + manifest_parent_prefix + " containing: " + data)

    metadata = data.split(',')
    metadata_dict = {}
    for val in metadata:
        split_val = val.split('=')
        metadata_dict[split_val[0]] = split_val[1]

    payload_data = {"package_id": "test_" + str(int(datetime.now().timestamp())),
                    "s3_path": manifest_parent_prefix,
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
                        "adminCategory": metadata_dict["adminCategory"]
                    }
                    }

    logging.debug("Including TESTTRIGGER")
    if key_exists(manifest_parent_prefix + "TESTTRIGGER"):
        payload_data["dry_run"] = "true"

    return payload_data


def get_parent_prefix(prefix):
    """
        Returns the parent prefix path of the given prefix
    """
    split_key = prefix.split('/')
    parent_prefix = ""
    for i in range(0, len(split_key) - 1):
        parent_prefix = parent_prefix + split_key[i] + "/"
    return parent_prefix


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

    logging.debug("Search for manifest-<algorithm>.txt file in bucket: " + epadd_bucket_name)

    epadd_bucket_objects = epadd_bucket.objects.all()
    for epadd_bucket_object in epadd_bucket_objects:
        if re.search('manifest(-md5|-sha256)?.txt', epadd_bucket_object.key, re.IGNORECASE):
            manifest_parent_prefix = get_parent_prefix(epadd_bucket_object.key)
            if not (key_exists(manifest_parent_prefix + "ingest.txt")
                    or key_exists(manifest_parent_prefix + "ingest.txt.failed")
                    or key_exists(manifest_parent_prefix + "LOADING")):
                logging.debug("Putting LOADING file at prefix: " + manifest_parent_prefix)
                s3_resource.Object(epadd_bucket_name, manifest_parent_prefix + "LOADING").put(Body="")
                manifest_object_keys.append(epadd_bucket_object.key)
                logging.debug("Object key added: " + epadd_bucket_object.key)

    return manifest_object_keys


def main():
    # Connect to s3 bucket
    logging.debug("Connect to S3 bucket")
    connect_to_bucket()

    # Collect exports
    export_object_keys = collect_exports()

    # Make ingest/ call to DIMS
    logging.debug("Calling DIMS /ingest for following objects: " + str(export_object_keys))

    for key in export_object_keys:
        call_dims_ingest(key)


try:
    main()
    sys.exit(0)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
