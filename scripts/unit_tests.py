#!/usr/bin/python3

import unittest, os, os.path
import unittest.mock as mock
import sys, traceback, shutil
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, '/home/appuser/epadd-curator-app/app')

import monitor_exports as monitor_epadd_exports

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
    

class MockEpaddBucketObject:
    def __init__(self, keyname):
        self.key = keyname

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

class MockEpaddBucket:
    def __init__(self):
        self.objects = MockEpaddBucketObjects()


class TestMonitorUnitCases(unittest.TestCase):

    @mock.patch("monitor_exports.s3_resource", MockS3Resource() )
    @mock.patch("monitor_exports.epadd_bucket_name", "test_bucket" )
    @mock.patch("monitor_exports.epadd_bucket", MockEpaddBucket() )
    def test_file_skip(self):
        filelist = monitor_epadd_exports.collect_exports()
        correctlist = ["test/manifest-sha256.txt/msdos.txt", "test/manifest-md5.txt/index.html"]
        self.assertEqual(filelist, correctlist)

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
        loading_file = os.path.join(download_export_path, "integration_testLOADING")
        os.remove(zip_file)
        os.remove(loading_file)
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
        payload = monitor_epadd_exports.construct_payload_body("/home/appuser/epadd-curator-app/resources/EmlExample")
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
        print("Zip path: " + zip_path)
        print("Eml path: " + eml_path)
        success = monitor_epadd_exports.zip_export(zip_export_path, eml_path)
        self.assertTrue(success, "Eml zip failed")
        self.assertTrue(os.path.isfile(zip_path))

if __name__ == '__main__':
    unittest.main()