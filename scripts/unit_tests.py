#!/usr/bin/python3

import unittest, os, os.path
import unittest.mock as mock
import sys, traceback, shutil
import py7zr, json, boto3
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, '/home/appuser/epadd-curator-app/app')

import monitor_exports as monitor_epadd_exports
from monitor_exports.monitor_exception import MonitoringException
from monitor_exports.monitor_exception import InvalidCharacterException
from monitor_exports.data_validator import DataValidator
import run_tests

class MockS3Resource:
    def __init__(self):
        pass
    
    def Object(self, argl, arg2):
        return MockS3ResourceObject()

class MockS3ResourceObject:
    def __init__(self, arg1, arg2):
        pass

    def __init__(self):
        pass

    def put(self, Body=""):
        pass
    
    def delete(self):
        pass
    

class MockEpaddBucketObject:
    def __init__(self, keyname):
        self.key = keyname
        
    def copy(self, source):
        pass

class MockEpaddBucketObjects:
    def __init__(self):
        self.files = []
        self.files.append( MockEpaddBucketObject("test/manifest-sha256.txt/msdos.txt") )
        self.files.append( MockEpaddBucketObject("test/manifest-md5.txt/index.html") )
        self.files.append( MockEpaddBucketObject("user/readme.txt") )
        self.files.append( MockEpaddBucketObject("user/") )   
        self.files.append( MockEpaddBucketObject("user") )
        self.files.append( MockEpaddBucketObject("test/user") )   

    def all(self):
        return self.files
    
    def filter(self, **kwargs):
        filtered_list = []
        if 'Prefix' not in kwargs:
            return self.files
        
        for file in self.files:
            if file.key.startswith(kwargs['Prefix']):
                filtered_list.append(file)
        return filtered_list

class MockEpaddBucket:
    def __init__(self):
        self.objects = MockEpaddBucketObjects()
        
class MockEpaddPerformanceTestingSourceBucketObjects:
    def __init__(self):
        self.files = []
        self.files.append( MockEpaddBucketObject("emltest1/data/somedata.txt") )
        self.files.append( MockEpaddBucketObject("emltest1/data/index.html") )
        self.files.append( MockEpaddBucketObject("emltest1/readme.txt") )
        self.files.append( MockEpaddBucketObject("emltest2/data/data2.txt") )   
        self.files.append( MockEpaddBucketObject("emltest2/readme2.txt") )
    
    def filter(self, **kwargs):
        filtered_list = []
        if 'Prefix' not in kwargs:
            return self.files
        
        for file in self.files:
            if file.key.startswith(kwargs['Prefix']):
                filtered_list.append(file)
        return filtered_list
            
    def all(self):
        return self.files

class MockEpaddPerformanceTestingSourceBucket:
    def __init__(self):
        self.objects = MockEpaddPerformanceTestingSourceBucketObjects()
        
class MockEpaddPerformanceTestingDesinationBucketObjects:
    def __init__(self):
        self.files = []
    
    def filter(self, **kwargs):
        filtered_list = []
        if 'Prefix' not in kwargs:
            return self.files
        
        for file in self.files:
            if file.key.startswith(kwargs['Prefix']):
                filtered_list.append(file)
        return filtered_list
            
    def all(self):
        return self.files
    
    def append(self, key):
        obj = MockEpaddBucketObject(key)
        self.files.append(obj)
        return obj
                
class MockEpaddPerformanceTestingDestinationBucket:
    def __init__(self):
        self.objects = MockEpaddPerformanceTestingDesinationBucketObjects()
        
    def upload_file(self, source, destination):
        obj = self.objects.append(destination)
        return obj
    
    def Object(self, key):
        obj = self.objects.append(key)
        return obj

  
class TestZipUnitCases(unittest.TestCase):
  
          
    def setUpClass():
        # create download and zip dirs if they don't exist
        download_export_path = "/home/appuser/epadd-curator-app/download_exports"
        zip_export_path = "/home/appuser/epadd-curator-app/zip_exports"
        if (not os.path.exists(download_export_path)):
            os.makedirs(download_export_path, exist_ok = True)
        if (not os.path.exists(zip_export_path)):
            os.makedirs(zip_export_path, exist_ok = True)
      
    def tearDownClass():
        download_export_path = "/home/appuser/epadd-curator-app/download_exports"
        zip_export_path = "/home/appuser/epadd-curator-app/zip_exports"
        zip_file = os.path.join(zip_export_path, "integration_test.7z")
        #loading_file = os.path.join(download_export_path, "integration_test/LOADING")
        os.remove(zip_file)
        #os.remove(loading_file)
        download_path = os.path.join(download_export_path, "integration_test")
        shutil.rmtree(download_path)

  
    def test_retrieve_export_1(self): #test download from S3
        try:
            download_export_path = "/home/appuser/epadd-curator-app/download_exports"
            manifest_parent_prefix = "integration_test"
            monitor_epadd_exports.connect_to_bucket()
            download_local_dir = monitor_epadd_exports.retrieve_export(download_export_path, manifest_parent_prefix)
            file_exists = os.path.exists(download_local_dir)
            dir_has_items = False
            if file_exists and not os.path.isfile(download_local_dir):
                if os.listdir(download_local_dir):
                    dir_has_items = True
        except:
            traceback.print_stack()
        self.assertEqual(True, file_exists)
        self.assertEqual(True, dir_has_items)
  
    def test_retrieve_export_2(self): #test zip of export
        download_export_path = "/home/appuser/epadd-curator-app/download_exports/integration_test"
        zip_export_path = "/home/appuser/epadd-curator-app/zip_exports"
        file_path = monitor_epadd_exports.zip_export(zip_export_path, download_export_path)
        file_exists = os.path.exists(file_path)
        self.assertEqual(True, file_exists)
      
    def test_retrieve_export_3(self): #test upload of export
        zip_path = "/home/appuser/epadd-curator-app/zip_exports/integration_test.7z"
        manifest_parent_prefix = "integration_test"
        success = monitor_epadd_exports.upload_zip_export(zip_path, manifest_parent_prefix)
        self.assertEqual(True, success)
  
class TestConstructPayload(unittest.TestCase):
  
    @mock.patch("monitor_exports.s3_resource", MockS3Resource() )
    @mock.patch("monitor_exports.epadd_bucket_name", "test_bucket" )
    @mock.patch("monitor_exports.epadd_bucket", MockEpaddBucket() )
    def test_construct_payload(self):
        payload = monitor_epadd_exports.construct_payload_body("/home/appuser/epadd-curator-app/resources/EmlExample", "")
        self.assertTrue(payload, "Payload returned was empty")
        
    def test_strip_unicode_tabs_and_blank_lines(self):
        mystring="LOWUSE\x00\x00\x00\x00\x00\x00"
        retval = monitor_epadd_exports.strip_unicode_and_whitespace(mystring)
        self.assertEqual(retval,"LOWUSE")
        mystring2="key=val         "
        retval2 = monitor_epadd_exports.strip_unicode_and_whitespace(mystring2)
        self.assertEqual(retval2,"key=val")
        mystring3="VALUE\u0000"
        retval3 = monitor_epadd_exports.strip_unicode_and_whitespace(mystring3)
        self.assertEqual(retval3,"VALUE")
          

class TestSendNotification(unittest.TestCase):
  
    def setUpClass():
        source = "/home/appuser/epadd-curator-app/resources/InvalidCharactersExample"
        dest = "/home/appuser/epadd-curator-app/download_exports/InvalidCharactersExample"
        #Copy InvalidCharactersExample from resources
        shutil.copytree(source,dest)
    
    def tearDownClass():
        #Remove the InvalidCharactersExample from download_exports
        shutil.rmtree("/home/appuser/epadd-curator-app/download_exports/InvalidCharactersExample")
            
    def test_notify(self):
        message = monitor_epadd_exports.send_error_notification("Test Subject from Curator App", "Test Body from Curator App", "dts@hu.onmicrosoft.com")
        json_message = json.loads(message)
        self.assertTrue(type(json_message) is dict)
        
    def test_monitoring_exception(self):
        e = MonitoringException("Message", "test@test.com")
        self.assertEqual(e.emailaddress, "test@test.com")
        
    def test_invalid_character_email(self):
        local_directory = "InvalidCharactersExample"
        message = monitor_epadd_exports.send_invalid_character_email(local_directory)
        json_message = json.loads(message)
        self.assertTrue(type(json_message) is dict)
        
         
class TestCopySingleExportFS(unittest.TestCase):
  
    @mock.patch("run_tests.s3_resource", MockS3Resource() )
    @mock.patch("run_tests.epadd_int_test_prefix_name", "" )
    @mock.patch("run_tests.epadd_source_type", "FS" )
    @mock.patch("run_tests.epadd_source_name", "/home/appuser/epadd-curator-app/resources" )
    @mock.patch("run_tests.epadd_bucket_name", "test_bucket" )
    @mock.patch("run_tests.epadd_bucket", MockEpaddPerformanceTestingDestinationBucket() )
    def test_copy_one(self):
        run_tests.copy_from_source_to_test('EmlExample')
        filelist = run_tests.epadd_bucket.objects.all()
        self.assertTrue(len(filelist)>100)
      
  
    def test_construct_payload(self):
        payload = monitor_epadd_exports.construct_payload_body("/home/appuser/epadd-curator-app/resources/EmlExample", "")
        self.assertTrue(payload, "Payload returned was empty")
        
class TestZipEpaddExports(unittest.TestCase):

        
    def setUpClass():
        resources_path = os.getenv("DATA_PATH", "/home/appuser/epadd-curator-app/resources")
        zip_export_path = os.getenv("ZIPPED_EXPORT_PATH", "/home/appuser/epadd-curator-app/zip_exports")
    
        # create download and zip dirs if they don't exist
        if (not os.path.exists(resources_path)):
            os.makedirs(resources_path, exist_ok = True)
        if (not os.path.exists(zip_export_path)):
            os.makedirs(zip_export_path, exist_ok = True)
            
    def tearDownClass():
        zip_export_path = os.getenv("ZIPPED_EXPORT_PATH", "/home/appuser/epadd-curator-app/zip_exports")
        zip_file = os.path.join(zip_export_path, "EmlExample.7z")
        os.remove(zip_file)

    def test_zip_eml(self): #zip an eml export
        resources_path = os.getenv("DATA_PATH", "/home/appuser/epadd-curator-app/resources")
        zip_export_path = os.getenv("ZIPPED_EXPORT_PATH", "/home/appuser/epadd-curator-app/zip_exports")
        zip_path = os.path.join(zip_export_path, "EmlExample.7z")
        eml_path = os.path.join(resources_path, "EmlExample")
        success = monitor_epadd_exports.zip_export(zip_export_path, eml_path)
        self.assertTrue(success, "Eml zip failed")
        self.assertTrue(os.path.isfile(zip_path))

        with py7zr.SevenZipFile(zip_path) as zip:
          files = zip.getnames()
          # 174 is number of files in test fixture: 'eml_path'
          self.assertTrue(len(files) == 174)
          for file in files:
            self.assertTrue(file.startswith("EmlExample"),
                            "File expected to start with 'EmlExample': {}".format(file))
            
class TestValidation(unittest.TestCase):

        
    def setUpClass():
        connect_to_bucket()
        download_export_path = os.getenv("DOWNLOAD_EXPORT_PATH", "/home/appuser/epadd-curator-app/download_exports")
        prefix = "user/ePADD-eml-export"
        destination_path = os.path.join(download_export_path, prefix)
        
        # create download dirs if they don't exist
        if (not os.path.exists(destination_path)):
            os.makedirs(destination_path, exist_ok = True)
        epadd_bucket.download_file(os.path.join(prefix, "manifest-sha256.txt"), os.path.join(destination_path, "manifest-sha256.txt"))
        
            
    def tearDownClass():
        download_export_path = os.getenv("DOWNLOAD_EXPORT_PATH", "/home/appuser/epadd-curator-app/download_exports")
        shutil.rmtree(os.path.join(download_export_path, "user"))
        
    def test_validation(self): 
        download_export_path = os.getenv("DOWNLOAD_EXPORT_PATH", "/home/appuser/epadd-curator-app/download_exports")
        prefix = "user/ePADD-eml-export"
        destination_path = os.path.join(download_export_path, prefix)
        manifest_file = os.path.join(destination_path, "manifest-sha256.txt")
        data_validator = DataValidator()
        self.assertTrue(data_validator.check_export_ready("epadd-export-dev", "user/ePADD-eml-export", manifest_file, s3_resource))
        
    def test_validation_invalid_characters(self): 
        manifest_file = "/home/appuser/epadd-curator-app/resources/InvalidCharactersExample/manifest-md5.txt"
        data_validator = DataValidator()
        with self.assertRaises(InvalidCharacterException):
            data_validator.check_export_ready("epadd-export-dev", "", manifest_file, s3_resource)
    
   
def connect_to_bucket():
    """
        Connect to the ePADD nextcloud s3 bucket
    """
    global s3_resource
    global epadd_bucket
    
    aws_access_key = os.getenv('NEXTCLOUD_AWS_ACCESS_KEY')
    aws_secret_key = os.getenv('NEXTCLOUD_AWS_SECRET_KEY')
    epadd_bucket_name = "epadd-export-dev"
    
    boto_session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key)

    # Then use the session to get the resource
    s3_resource = boto_session.resource('s3')

    epadd_bucket = s3_resource.Bucket(epadd_bucket_name)

if __name__ == '__main__':
    unittest.main()
