const fs = require('fs');
const path = require('path');
const CONSTANTS = require('../config/constants');

const validateRangeHeader = async (req, res, next) => {
  const range = req.headers.range;
  const filePath = path.join(CONSTANTS.CONTENTS_DIR, decodeURIComponent(req.path));
  
  try {
    const stats = await fs.promises.stat(filePath);
    const fileSize = stats.size;

    if (range) {
      const parts = range.replace(/bytes=/, "").split("-");
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;

      if (start >= fileSize || end >= fileSize) {
        return res.status(416).json({ error: 'Requested Range Not Satisfiable' });
      }

      res.writeHead(206, {
        'Content-Range': `bytes ${start}-${end}/${fileSize}`,
        'Accept-Ranges': 'bytes',
        'Content-Length': (end - start) + 1,
        'Content-Type': 'video/mp4',
      });

      fs.createReadStream(filePath, { start, end }).pipe(res);

      return;
    }

    next();
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
};

module.exports = { validateRangeHeader };

