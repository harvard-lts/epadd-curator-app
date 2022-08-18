const Cron = require("croner");
const fs = require("fs");
const {spawn} = require("child_process");
const dotenv = require('dotenv');
dotenv.config();

// Set cron intervals
second = process.env.SECOND
minute = process.env.MINUTE
hour = process.env.HOUR
day = process.env.DAY
month = process.env.MONTH
day_of_week = process.env.DAY_OF_WEEK
interval = `${second} ${minute} ${hour} ${day} ${month} ${day_of_week}`


/*    ┌──────────────── (optional) second (0 - 59)
      │ ┌────────────── minute (0 - 59)
      │ │ ┌──────────── hour (0 - 23)
      │ │ │ ┌────────── day of month (1 - 31)
      │ │ │ │ ┌──────── month (1 - 12, JAN-DEC)
      │ │ │ │ │ ┌────── day of week (0 - 6, SUN-Mon)
      │ │ │ │ │ │       (0 to 6 are Sunday to Saturday; 7 is Sunday, the same as 0)
      │ │ │ │ │ │       */
Cron(interval, {}, ()=> {
  console.log("checking for epadd exports in Nextcloud buckets");

  try {
    subprocess = spawn("/home/appuser/epadd-curator-app/monitor_epadd_exports.py")
    subprocess.stdout.on('data', (data) => { console.log(data.toString()) });
    subprocess.stderr.on('data', (data) => { console.log("ERR: " + data) });
  }
  catch (e) {
    console.log(e);
  }

});
