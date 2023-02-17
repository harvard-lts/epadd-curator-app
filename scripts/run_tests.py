#!/usr/bin/python3
import sys
import traceback

sys.path.insert(0, '/home/appuser/epadd-curator-app/app')

import run_tests



def main(argv):
    run_tests.connect_to_buckets()

    # Run single export
    if len(argv) > 0 and argv[0] != "":
        run_tests.copy_export(str(argv[0]))
    #Run all exports
    else:
        run_tests.copy_all_exports()

try:
    main(sys.argv[1:])
    sys.exit(0)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
