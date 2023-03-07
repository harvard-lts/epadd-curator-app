// app for healthcheck and integration tests

const express = require('express');
const app = express();
const port = 8443

var fs = require('fs'),
    http = require('http'),
    https = require('https');

const options = {
   key: fs.readFileSync('/home/appuser/ssl/certs/server.key', 'utf8'),
   cert: fs.readFileSync('/home/appuser/ssl/certs/server.crt', 'utf8')
};

var server = https.createServer(options, app);

server.listen(port, () => {
   console.log('Server running on port: ${port}');
});

app.use('/', require('./routes/healthcheck.js'));
app.use('/', require('./routes/integrationTest.js'));