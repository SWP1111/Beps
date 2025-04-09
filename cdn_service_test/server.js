const express = require('express');
const bodyParser = require('body-parser');
const routes = require('./routes/routes');

const app = express();
const port = 3001;

app.use(bodyParser.json());
app.use('/', routes);

app.listen(port, () => {
  console.log(`Video server running at http://localhost:${port}`);
});