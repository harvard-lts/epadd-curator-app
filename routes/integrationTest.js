const express = require('express');
const app = express();
const router = express.Router();
const {spawn} = require("child_process");

router.get('/testExport', (request, response) => {
      console.log("Calling test export script");
      var testOSN = request.query.osn;
      if(testOSN == undefined){
        testOSN = "";
      }

      try {
        subprocess = spawn('python3', ["/home/appuser/epadd-curator-app/scripts/test_export.py", testOSN])
        subprocess.stdout.on('data', (data) => { console.log(data.toString()) });
        subprocess.stderr.on('data', (data) => { console.log("ERR: " + data) });
        response.json({"status": "success"});
      }
      catch (e) {
        console.log(e);
        response.json({"status": "failure"});
      }
});

router.get('/runAllTests', (request, response) => {
    console.log("Calling run test script");


    try {
      subprocess = spawn('python3', ["/home/appuser/epadd-curator-app/scripts/run_tests.py"])
      subprocess.stdout.on('data', (data) => { console.log(data.toString()) });
      subprocess.stderr.on('data', (data) => { console.log("ERR: " + data) });
      response.json({"status": "success"});
    }
    catch (e) {
      console.log(e);
      response.json({"status": "failure"});
    }
});

router.get('/runTest/:dirName', (request, response) => {
    console.log("Calling run test script");
    var dirName = "";
    if(request.params.dirName){
    	dirName = request.params.dirName;
    }

    try {
      subprocess = spawn('python3', ["/home/appuser/epadd-curator-app/scripts/run_tests.py", dirName])
      subprocess.stdout.on('data', (data) => { console.log(data.toString()) });
      subprocess.stderr.on('data', (data) => { console.log("ERR: " + data) });
      response.json({"status": "success"});
    }
    catch (e) {
      console.log(e);
      response.json({"status": "failure"});
    }
});

module.exports = router