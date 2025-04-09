const jwt = require('jsonwebtoken');
const CONSTANTS = require('../config/constants');

const authenticateJwtHeader = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (token == null) return res.sendStatus(401);
  jwt.verify(token, CONSTANTS.SECRET_KEY, (err, user) => {
      if (err) return res.sendStatus(403);
      req.user = user;
      next();
  });
};

const authenticateJwtQuery = (req, res, next) => {
  const token = req.query.token;
  if (token == null) return res.sendStatus(401);
  jwt.verify(token, CONSTANTS.SECRET_KEY, (err, user) => {
      if (err) return res.sendStatus(403);
      req.user = user;
      next();
  });
};

module.exports = { authenticateJwtHeader, authenticateJwtQuery };
