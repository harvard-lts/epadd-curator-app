// app for healthcheck and integration tests

const express = require('express');
const app = express();
const port = 8443

app.listen(port, () => {
   console.log(`Server running on port: ${port}`);
});

app.use('/', require('./routes/healthcheck.js'));
app.use('/', require('./routes/integrationTest.js'));