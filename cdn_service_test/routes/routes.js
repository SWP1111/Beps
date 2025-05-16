const express = require('express');
const jwt = require('jsonwebtoken');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const { authenticateJwtHeader, authenticateJwtQuery } = require('../auth/auth');
const { getDirectories, getDirectoryTree } = require('../utils/fileUtils');
const { validateRangeHeader } = require('../middleware/rangeValidator');

const CONSTANTS = require('../config/constants');
const pool = require('../config/db');

const router = express.Router();
const service_type = "cdn";

router.post('/login', (req, res) => {
  const { username, password } = req.body;
  if (password === CONSTANTS.PASSWORD) {
    const token = jwt.sign({ username }, CONSTANTS.SECRET_KEY, { expiresIn: '2h' });
    res.json({ token });
    console.log(`login`);
  } else {
    res.status(401).send('Invalid credentials');
    console.log(`loInvalid credentialsgin`);
  }
});

// 전체 "채널" 조회
router.get('/list-directories', authenticateJwtHeader, (req, res) => {
  try {
    res.json(getDirectories(CONSTANTS.CONTENTS_DIR));
  } catch {
    res.status(500).json({ error: 'Unable to scan directory' });
  }
});

router.get(`/${service_type}/list-directories`, authenticateJwtHeader, async (req, res) => {
  try {
    const query = `
      SELECT id, name
      FROM content_rel_channels
      WHERE is_deleted = false
    `;

    const result = await pool.query(query);
    res.json(result.rows); // [{ id: 1, name: '채널1' }, { id: 2, name: '채널2' }, ...]
    console.log(`/${service_type}/list-directories`);
  } catch (err) {    
    res.status(500).json({ message: '채널 정보를 불러올 수 없어요.' });
    console.error(`/${service_type}/list-directories`, err);
  }
});

// 특정 "채널" 의 하위 전체 목록 조회
router.get('/list-directories/*', authenticateJwtHeader, (req, res) => {
  const folderPath = path.join(CONSTANTS.CONTENTS_DIR, req.params[0]);
  if (!fs.existsSync(folderPath)) return res.status(404).json({ error: 'Folder not found' });
  res.json(getDirectoryTree(folderPath));
});

router.get(`/${service_type}/list-directories/*`, async (req, res) => {
  try {
    const id = parseInt(req.params[0], 10); // 문자열을 정수로 바꿔요
    console.log(`id = ${id}`);

    if (isNaN(id)) {
      return res.status(400).json({ message: '올바르지 않은 ID입니다.' });
    }

    const query = `
SELECT
  ch.name AS channel_name,
  fo.id AS folder_id,
  fo.name AS folder_name,
  pg.id AS page_id,
  pg.name AS page_name
FROM content_rel_channels ch
JOIN content_rel_folders fo ON fo.channel_id = ch.id AND fo.is_deleted = false
JOIN content_rel_pages pg ON pg.folder_id = fo.id AND pg.is_deleted = false
WHERE ch.id = $1
  AND ch.is_deleted = false;
    `;

    const result = await pool.query(query, [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ message: '해당 ID의 채널을 찾을 수 없어요.' });
    }

    res.json(result.rows[0]); // 하나만 반환
  } catch (err) {
    console.error('채널 데이터 조회 중 오류:', err);
    res.status(500).json({ message: '채널 정보를 불러올 수 없어요.' });
  }
});

// 해당 페이지 보기
router.use('/contents-view', authenticateJwtQuery, validateRangeHeader, express.static(CONSTANTS.CONTENTS_DIR, {
  acceptRanges: true,
  setHeaders: (res, path, stat) => {
    res.setHeader('Accept-Ranges', 'bytes');
    console.log(`res : ${res}`);
    console.log(`path : ${path}`);
    console.log(`stat : ${stat}`);
  }
}));

// 해당 페이지의 상세보기 정보 조회
router.get('/view-details/*', authenticateJwtQuery, (req, res) => {
  const filePath = path.join(CONSTANTS.CONTENTS_DIR, req.params[0]);
  if (!fs.existsSync(filePath) || !filePath.endsWith('DraggableButtonMargins.json'))
    return res.status(404).json({ error: 'Details file not found' });
  fs.readFile(filePath, 'utf8', (err, data) => {
    if (err) return res.status(500).json({ error: 'Unable to read file' });
    res.send(data);
  });
});

// 설치버전 다운로드
router.use(`/${service_type}/download-installer/*`, authenticateJwtQuery, validateRangeHeader, (req, res) => {
  const filePath = path.join(CONSTANTS.APPLICATION_DIR, req.params[0]);

  console.log(`filename : ${req.params[0]}`);
  console.log(`[INFO] Requested filename: ${req.params[0]}`);

  if (!req.params[0] || !fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  const stat = fs.statSync(filePath);
  const fileSize = stat.size;
  const range = req.headers.range;

  if (range) {
    // Parse the Range header
    const parts = range.replace(/bytes=/, '').split('-');
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;

    if (start >= fileSize || end >= fileSize) {
      res.status(416).json({ error: 'Requested range not satisfiable' });
      return;
    }

    const chunkSize = end - start + 1;
    const fileStream = fs.createReadStream(filePath, { start, end });

    res.writeHead(206, {
      'Content-Range': `bytes ${start}-${end}/${fileSize}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': chunkSize,
      'Content-Type': 'application/octet-stream',
    });

    fileStream.pipe(res);
  } else {
    // No Range header, send the entire file
    res.writeHead(200, {
      'Content-Length': fileSize,
      'Content-Type': 'application/octet-stream',
    });

    fs.createReadStream(filePath).pipe(res);
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

// latest 버전 조회
router.get(`/${service_type}/get-exe-version`, (req, res) => {
  const exePath = path.join(CONSTANTS.APPLICATION_DIR, "bepsapp.exe");
  if (!fs.existsSync(exePath)) return res.status(404).json({ error: 'File not found' });
  exec(`strings ${exePath} | grep -i "version"`, (err, stdout) => {
    if (err || !stdout.trim()) return res.status(500).json({ error: 'No version info found' });
    res.json({ version: stdout.replace(/[^     res.json({ version: stdout.replace(/[^\x20-\x7E]/g, '').trim() });
  });
});

// 설치버전 다운로드
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

module.exports = router;
