const express = require('express');
const app = express();
const router = express.Router();
const {spawn} = require("child_process");

router.get('/testExport/:testOSN?', (request, response) => {
      console.log("Calling test export script");
      var testOSN = "";
      if(request.params.testOSN){
        testOSN = request.params.testOSN;
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

module.exports = router