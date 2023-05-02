#!/usr/bin/python3
import logging, boto3, os, botocore, re
from monitor_exports.monitor_exception import ValidationException
from monitor_exports.monitor_exception import InvalidCharacterException

logger = logging.getLogger('monitor_epadd_exports')

class DataValidator:
    
    def check_export_ready(self, bucket_name, prefix_path, local_manifest_file_location, s3_resource):
        '''Verifies that the export is ready and that it has no invalid characters.  
        Invalid characters:
        1.    < (less than)
        2.    > (greater than)
        3.    : (colon)
        4.    " (double quote)
        5.    / (forward slash)
        6.    \ (backslash)
        7.    | (vertical bar or pipe)
        8.    ? (question mark)
        9.    * (asterisk)
        10.   ~ (tilde)
        '''

        #Read each line of the manifest and get the prefix path
        with open(local_manifest_file_location) as file:
            for line in file:
                if line.strip():
                    split_values = line.split(" ",1)
                    if (len(split_values) != 2):
                        raise ValidationException("Manifest file {} improperly formatted.".format(local_manifest_file_location))
                    
                    base_file_name = os.path.basename(split_values[1].strip())
                    print(base_file_name)
                    if (re.search("<|>|:|\?|~|\"|\/|\\|\||\*", base_file_name)):
                        raise InvalidCharacterException("Attempting to upload a file that is not supported by NextCloud {}.".format(split_values[1]))
                        
                    path_to_object = os.path.join(prefix_path, split_values[1].strip())
                    if not self.__object_exists(s3_resource, bucket_name, path_to_object):
                        logger.error("{} does not exist in {}".format(path_to_object, bucket_name))
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