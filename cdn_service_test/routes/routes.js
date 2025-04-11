const express = require('express');
const jwt = require('jsonwebtoken');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const { authenticateJwtHeader, authenticateJwtQuery } = require('../auth/auth');
const { getDirectories, getDirectoryTree } = require('../utils/fileUtils');
const { validateRangeHeader } = require('../middleware/rangeValidator');

const CONSTANTS = require('../config/constants');
const router = express.Router();
const service_type = "cdn";

router.post('/login', (req, res) => {
  const { username, password } = req.body;
  if (password === CONSTANTS.PASSWORD) {
    const token = jwt.sign({ username }, CONSTANTS.SECRET_KEY, { expiresIn: '2h' });
    res.json({ token });
    console.log(`token`);
  } else {
    res.status(401).send('Invalid credentials');
    console.log(`loInvalid credentialsgin`);
  }
});

router.get(`/${service_type}/get-exe-version`, (req, res) => {
  const exePath = path.join(CONSTANTS.APPLICATION_DIR, "bepsapp.exe");
  if (!fs.existsSync(exePath)) return res.status(404).json({ error: 'File not found' });
  exec(`strings ${exePath} | grep -i "version"`, (err, stdout) => {
    if (err || !stdout.trim()) return res.status(500).json({ error: 'No version info found' });
    res.json({ version: stdout.replace(/[^     res.json({ version: stdout.replace(/[^\x20-\x7E]/g, '').trim() });
  });
});

router.get(`/${service_type}/get-installer-version`, (req, res) => {
  const files = fs.readdirSync(CONSTANTS.APPLICATION_DIR);
  const exeFile = files.find(file => file.endsWith('.exe'));

  if (!exeFile) return res.status(404).json({ error: 'File not found' });

  const versionMatch = exeFile.match(/_(\d+\.\d+\.\d+)\.exe$/);
  if (!versionMatch) {
    return res.status(500).json({ error: 'No version info found' });
  }

  const version = versionMatch[1];
  res.json({ version });
});

router.get(`/${service_type}/get-installer-name/:appname`, (req, res) => {
  try {
    const filePath = path.join(CONSTANTS.APPLICATION_DIR, req.params.appname);
    const files = fs.readdirSync(filePath).filter(file => file.endsWith('.exe') || file.endsWith('.zip'));

    if (files.length === 0) {
      return res.status(404).json({ error: 'No .exe files found' });
    }

    // 내림차순으로 정렬
    files.sort((a, b) => b.localeCompare(a));

    // 첫 번째 파일 반환
    res.json({ name: files[0] });
  } catch (error) {
    console.error(`Error reading directory: ${error.message}`);
    res.status(500).json({ error: 'Unable to read directory' });
  }
});

router.use(`/${service_type}/download-installer-path/:appname`, authenticateJwtQuery, validateRangeHeader, (req, res) => {
  try {
    const filePath = path.join(CONSTANTS.APPLICATION_DIR, req.params.appname);
    const files = fs.readdirSync(filePath).filter(file => file.endsWith('.exe') || file.endsWith('.zip'));

    if (files.length === 0) {
      return res.status(404).json({ error: 'No .exe files found' });
    }

    // 내림차순으로 정렬
    files.sort((a, b) => b.localeCompare(a));

    // 첫 번째 파일 반환
    //    res.json({ name: files[0] });
    const file = path.join(filePath, files[0]);
    if (!fs.existsSync(file)) {
      return res.status(404).json({ error: 'File not found' });
    }

    res.download(file, err => {
      if (err) {
        console.error(`Error downloading file: ${err.message}`);
        res.status(500).json({ error: 'Unable to download file' });
      }
    });
  } catch (error) {
    console.error(`Error reading directory: ${error.message}`);
    res.status(500).json({ error: 'Unable to read directory' });
  }


});

/*
router.use('/download-installer', authenticateJwtQuery, validateRangeHeader, express.static(CONSTANTS.APPLICATION_DIR, {
  acceptRanges: true,
  setHeaders: (res, path, stat) => {
    res.setHeader('Accept-Ranges', 'bytes');
    console.log(`res : ${res}`);
    console.log(`path : ${path}`);
    console.log(`stat : ${stat}`);
  }
}));
*/

router.use(`/${service_type}/download-installer/:filename`, authenticateJwtQuery, validateRangeHeader, (req, res) => {
  const filePath = path.join(CONSTANTS.APPLICATION_DIR, req.params.filename);

  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  res.download(filePath, err => {
    if (err) {
      console.error(`Error downloading file: ${err.message}`);
      res.status(500).json({ error: 'Unable to download file' });
    }
  });
});

router.get('/list-directories', authenticateJwtHeader, (req, res) => {
  try {
    res.json(getDirectories(CONSTANTS.CONTENTS_DIR));
  } catch {
    res.status(500).json({ error: 'Unable to scan directory' });
  }
});

router.get('/list-directories/*', authenticateJwtHeader, (req, res) => {
  const folderPath = path.join(CONSTANTS.CONTENTS_DIR, req.params[0]);
  if (!fs.existsSync(folderPath)) return res.status(404).json({ error: 'Folder not found' });
  res.json(getDirectoryTree(folderPath));
});

router.use('/contents-view', authenticateJwtQuery, validateRangeHeader, express.static(CONSTANTS.CONTENTS_DIR, {
  acceptRanges: true,
  setHeaders: (res, path, stat) => {
    res.setHeader('Accept-Ranges', 'bytes');
    console.log(`res : ${res}`);
    console.log(`path : ${path}`);
    console.log(`stat : ${stat}`);
  }
}));

router.get('/view-details/*', authenticateJwtQuery, (req, res) => {
  const filePath = path.join(CONSTANTS.CONTENTS_DIR, req.params[0]);
  if (!fs.existsSync(filePath) || !filePath.endsWith('DraggableButtonMargins.json'))
    return res.status(404).json({ error: 'Details file not found' });
  fs.readFile(filePath, 'utf8', (err, data) => {
    if (err) return res.status(500).json({ error: 'Unable to read file' });
    res.send(data);
  });
});

module.exports = router;
