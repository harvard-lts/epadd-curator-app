#!/usr/bin/python3

import sys, traceback, os
sys.path.insert(0, '/home/appuser/epadd-curator-app/app')

import monitor_exports

is_testing = os.getenv("TESTING", "False")


def main():
    # Connect to s3 bucket
    #This wil pollute the logs if we are only testing.
    if is_testing != "True":
        print("Connect to S3 bucket")
    monitor_exports.connect_to_bucket()

    # Collect exports
    export_object_keys = monitor_exports.collect_exports()

    #This wil pollute the logs if we are only testing.
    if is_testing != "True":
        # Make ingest/ call to DIMS
        print("Calling DIMS /ingest for following objects: " + str(export_object_keys))

    if is_testing != "True":
        for key in export_object_keys:
            monitor_exports.call_dims_ingest(key)

if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
