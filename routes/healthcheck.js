const express = require('express');
const app = express();
const router = express.Router();

router.get('/healthcheck', (request, response) => {
   try{
      response.json({"status": "OK!", "uptime": process.uptime(), "timestamp": Date.now()});
   } catch (error) {
      response.status(503).send();
   }
});

module.exports = router