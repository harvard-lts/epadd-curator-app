#!/usr/bin/python3
import json
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
from requests import exceptions, get, HTTPError

DATEFORMAT = '%Y-%m-%d %H:%M:%S'
relative_dir = os.path.dirname(os.path.realpath(__file__))
logname_template = os.path.dirname(os.path.realpath(__file__)) + "/logs/monitor_epadd_exports_{}.log"
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


def call_dims_ingest(s3_resource, manifest_object_key):
    with open(jwt_private_key_path) as jwt_private_key_file:
        jwt_private_key = jwt_private_key_file.read()

    # TODO: Get metadata info from sidecar files
    payload_data = {"package_id": "test",
                    "s3_path": "test",
                    "s3_bucket_name": "test",
                    "admin_metadata":
                        {"accessFlag": "N",
                         "contentModel": "opaque",
                         "depositingSystem": "Harvard Dataverse",
                         "firstGenerationInDrs": "unspecified",
                         "objectRole": "CG:DATASET",
                         "usageClass": "LOWUSE",
                         "storageClass": "AR",
                         "ownerCode": "123",
                         "billingCode": "456",
                         "resourceNamePattern": "pattern",
                         "urnAuthorityPath": "path",
                         "depositAgent": "789",
                         "depositAgentEmail": "someone@mailinator.com",
                         "successEmail": "winner@mailinator.com",
                         "failureEmail": "loser@mailinator.com",
                         "successMethod": "method",
                         "adminCategory": "root"}
                    }

    # calculate iat and exp values
    current_datetime = datetime.now()
    current_epoch = int(current_datetime.timestamp())
    expiration = current_datetime + timedelta(seconds=jwt_expiration)

    # get request_body hash
    request_body = jcs.canonicalize(payload_data).decode()
    bodySHA256Hash = hashlib.sha256(request_body.encode()).hexdigest()

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

    manifest_parent_prefix = get_parent_prefix(manifest_object_key)
    if json_ingest_response["status"] == "failure":
        logging.debug("Putting ingest.txt.failed at prefix: " + manifest_parent_prefix)
        content = ""
        s3_resource.Object(epadd_bucket_name, manifest_parent_prefix + "ingest.txt.failed").put(Body=content)
    else:
        content = "Pending ingest.."
        s3_resource.Object(epadd_bucket_name, manifest_parent_prefix + "ingest.txt").put(Body=content)


def get_parent_prefix(prefix):
    split_key = prefix.split('/')
    parent_prefix = ""
    for i in range(0, len(split_key) - 1):
        parent_prefix = parent_prefix + split_key[i] + "/"
    return parent_prefix


def main():
    export_object_keys = []

    # Search for manifest file
    logging.debug("Connect to S3 bucket")

    # Change session code
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key)

    # Then use the session to get the resource
    s3 = session.resource('s3')

    epadd_bucket = s3.Bucket(epadd_bucket_name)
    logging.debug("Connected to S3 bucket: " + epadd_bucket_name)

    logging.debug("Search for manifest-<algorithm>.txt file in bucket: " + epadd_bucket_name)

    epadd_bucket_objects = epadd_bucket.objects.all()
    for epadd_bucket_object in epadd_bucket_objects:
        if re.search('manifest(-md5|-sha256)?.txt', epadd_bucket_object.key, re.IGNORECASE):
            if (get_parent_prefix(epadd_bucket_object.key) + "ingest.txt" not in epadd_bucket_objects and
                    get_parent_prefix(epadd_bucket_object.key) + "ingest.txt.failed" not in epadd_bucket_objects):
                export_object_keys.append(epadd_bucket_object.key)
                logging.debug("Object key added: " + epadd_bucket_object.key)

    # Make ingest/ call to DIMS
    for key in export_object_keys:
        call_dims_ingest(s3, key)


try:
    main()
    sys.exit(0)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
