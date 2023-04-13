#!/usr/bin/python3

import sys, traceback, os, logging
from datetime import datetime, timedelta
sys.path.insert(0, '/home/appuser/epadd-curator-app/app')

import monitor_exports
from monitor_exports.monitor_exception import MonitoringException

is_testing = os.getenv("TESTING", "False")

DATEFORMAT = '%Y-%m-%d %H:%M:%S'
log_dir = os.getenv("LOG_DIR", "/home/appuser/epadd-curator-app/logs")
log_level = os.getenv("LOG_LEVEL", "WARNING")
logname_template = os.path.join(log_dir, "monitor_epadd_exports_{}.log")
logging.basicConfig(filename=logname_template.format(datetime.today().strftime("%Y%m%d")),
                    format='%(asctime)-2s --%(filename)s-- %(levelname)-8s %(message)s', datefmt=DATEFORMAT,
                    level=log_level)

def main():
    # Connect to s3 bucket
    #This wil pollute the logs if we are only testing.
    if is_testing != "True":
        logging.debug("Connect to S3 bucket")
    monitor_exports.connect_to_bucket()

    # Collect exports
    export_object_keys = monitor_exports.collect_exports()

    #This wil pollute the logs if we are only testing.
    if is_testing != "True":
        # Make ingest/ call to DIMS
        logging.info("Calling DIMS /ingest for following objects: " + str(export_object_keys))

    if is_testing != "True":
        for key in export_object_keys:
            try:
                monitor_exports.call_dims_ingest(key)
            except MonitoringException as m:
                message = traceback.format_exc()
                logging.error(message)
                monitor_exports.send_error_notification(str(m), message, m.emailaddress)
            except Exception as e:  
                message = traceback.format_exc()
                logging.error(message)
                monitor_exports.send_error_notification(str(e), message) 
            
if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)