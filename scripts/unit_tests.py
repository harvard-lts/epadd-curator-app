#!/usr/bin/python3

import unittest, os, os.path
import unittest.mock as mock
os.environ['JWT_EXPIRATION'] = '99999999'
import monitor_epadd_exports

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

    @mock.patch("monitor_epadd_exports.s3_resource", MockS3Resource() )
    @mock.patch("monitor_epadd_exports.epadd_bucket_name", "test_bucket" )
    @mock.patch("monitor_epadd_exports.epadd_bucket", MockEpaddBucket() )
    def test_skip(self):
        filelist = monitor_epadd_exports.collect_exports()
        correctlist = ["test/manifest-sha256.txt/msdos.txt", "test/manifest-md5.txt/index.html"]
        self.assertEqual(filelist, correctlist)


class TestMonitorIntegrationCases(unittest.TestCase):

       def test_retrieve_export(self):
        manifest_parent_prefix = "integration_test/"
        zip_path = "./"
        zip_local_dir = monitor_epadd_exports.retrieve_export()
        file_exists = os.path.exists(zip_local_dir)
        self.assertEqual(True, file_exists)
        self.assertEqual(True, file_exists)

    def test_zip_export(self):
        zip_path = "./"
        manifest_parent_prefix = "integration_test/"
        file_path = monitor_epadd_exports.zip_export(zip_path, manifest_parent_prefix)
        file_exists = os.path.exists(file_path)
        dir_has_items = False
        if os.path.exists(file_path) and not os.path.isfile(file_path):
            if os.listdir(path):
                dir_has_items = True
        self.assertEqual(True, file_exists)
        self.assertEqual(True, dir_has_items)
    
    def test_upload_zip_export(self):
        zip_path = "./integration_test/integration_test.7z"
        manifest_parent_prefix = "integration_test/"
        success = upload_zip_export(zip_path, manifest_parent_prefix)
        self.assertEqual(True, success)



if __name__ == '__main__':
    unittest.main()