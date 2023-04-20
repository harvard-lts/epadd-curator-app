#!/usr/bin/python3
import logging, boto3, os, botocore
from monitor_exports.monitor_exception import ValidationException

logger = logging.getLogger('monitor_epadd_exports')

class DataValidator:
    
    def check_export_ready(self, bucket_name, prefix_path, local_manifest_file_location, s3_resource):
        #Read each line of the manifest and get the prefix path
        with open(local_manifest_file_location) as file:
            for line in file:
                if line.strip():
                    split_values = line.split(" ",1)
                    if (len(split_values) != 2):
                        raise ValidationException("Manifest file {} improperly formatted.".format(local_manifest_file_location))
                    path_to_object = os.path.join(prefix_path, split_values[1].strip())
                    if not self.__object_exists(s3_resource, bucket_name, path_to_object):
                        logger.debug("{} does not exist in {}".format(path_to_object, bucket_name))
                        return False
        #If it doesn't fail, then it is ready
        return True
    
    def __object_exists(self, s3_resource, bucket_name, path_to_object):
        try:
            s3_resource.Object(bucket_name, path_to_object).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            else:
                # Something else has gone wrong.
                raise e
        return True