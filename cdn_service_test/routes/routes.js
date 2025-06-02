const express = require('express');
const jwt = require('jsonwebtoken');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const { authenticateJwtHeader, authenticateJwtQuery } = require('../auth/auth');
const { getDirectories, getDirectoryTree } = require('../utils/fileUtils');
const { validateRangeHeader } = require('../middleware/rangeValidator');

const CONSTANTS = require('../config/constants');
const dbPool = require('../config/db');

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


router.get(`/${service_type}/list-directories`, async (req, res) => {
  try {
    const query = `
      SELECT id, name
      FROM content_rel_channels
      WHERE is_deleted = false ORDER BY name
    `;

    const result = await dbPool.query(query);

    // 숫자 추출 후 오름차순 정렬
    const sorted = result.rows.sort((a, b) => {
      const numA = parseInt(a.name.split('_')[0]) || 0;
      const numB = parseInt(b.name.split('_')[0]) || 0;
      return numA - numB;
    });

    res.json(sorted);

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


router.get(`/${service_type}/list-directories/:channelId`, async (req, res) => {
  const channelId = parseInt(req.params.channelId);
  if (!channelId) {
    return res.status(400).json({ error: 'channelId를 URL 파라미터로 전달해주세요.' });
  }
  try {
    const data = await getFoldersWithPages(channelId);
    res.json(data);
  } catch (error) {
    console.error('에러 발생:', error.message);
    res.status(500).json({ error: error.message });
  }
});


// 폴더별로 하위 페이지를 포함한 구조로 반환
async function getFoldersWithPages(channelId) {
  // 폴더 조회
  const { rows: folders } = await dbPool.query(
    `SELECT * FROM content_rel_folders WHERE channel_id = $1 AND is_deleted = false ORDER BY id`,
    [channelId]
  );

  // 페이지 전체 조회
  const { rows: pages } = await dbPool.query(
    `SELECT * FROM content_rel_pages WHERE is_deleted = false ORDER BY id`
  );

  // 폴더별로 묶기
  const folderItems = folders.map(folder => {
    const pageItems = pages
      .filter(page => page.folder_id === folder.id)
      .map(page => ({ pageItem: page }));

    return {
      folderItem: {
        ...folder,
        pageItems
      }
    };
  });

  return { folderItems };
}


// 해당 페이지의 상세페이지 조회
router.get(`/${service_type}/page/:pageId`, async (req, res) => {
  const pageId = parseInt(req.params.pageId);
  if (!pageId) {
    return res.status(400).json({ error: 'pageId를 URL 파라미터로 전달해주세요.' });
  }
  try {
    const { rows } = await dbPool.query(
      `SELECT * FROM content_rel_page_details WHERE page_id = $1 AND is_deleted = false ORDER BY id`,
      [pageId]
    );
    res.json(rows);
  } catch (error) {
    console.error('에러 발생:', error.message);
    res.status(500).json({ error: error.message });
  }
});

router.put(`/${service_type}/page-detail/:id/margin`, async (req, res) => {
  const id = parseInt(req.params.id, 10);
  const { margin } = req.body;
  if (!id) {
    return res.status(400).json({ error: 'id를 URL 파라미터로 전달해주세요.' });
  }
  if (typeof margin === 'undefined') {
    return res.status(400).json({ error: 'margin 값을 body에 전달해주세요.' });
  }
  try {
    const result = await dbPool.query(
      `UPDATE content_rel_page_details SET margin = $1, updated_at = now() WHERE id = $2 RETURNING *`,
      [margin, id]
    );
    if (result.rowCount === 0) {
      return res.status(404).json({ error: '해당 id의 page_detail을 찾을 수 없습니다.' });
    }
    res.json(result.rows[0]);
  } catch (error) {
    console.error('에러 발생:', error.message);
    res.status(500).json({ error: error.message });
  }
});

// 하위 폴더 재귀 조회
async function getSubFolders(parentId, channelId) {
  const query = parentId === null
    ? `SELECT * FROM content_rel_folders WHERE parent_id IS NULL AND channel_id = $1 AND is_deleted = false`
    : `SELECT * FROM content_rel_folders WHERE parent_id = $1 AND channel_id = $2 AND is_deleted = false`;

  const params = parentId === null ? [channelId] : [parentId, channelId];
  const { rows: folders } = await dbPool.query(query, params);

  folders.sort((a, b) => {
    const numA = parseInt(a.name.split('_')[0], 10) || 0;
    const numB = parseInt(b.name.split('_')[0], 10) || 0;
    return numA - numB;
  });

  for (const folder of folders) {
    //folder.attributes = { ...folder };
    delete folder.folders;
    delete folder.pages;

    folder.folders = await getSubFolders(folder.id, channelId);
    folder.pages = await getPages(folder.id);

    if (folder.pages && folder.pages.length) {
      folder.pages.sort((a, b) => {
        const numA = parseInt(a.attributes.name.split('_')[0], 10) || 0;
        const numB = parseInt(b.attributes.name.split('_')[0], 10) || 0;
        return numA - numB;
      });
    }

    // folders, pages가 비어있으면 삭제 (선택사항)
    if (folder.folders.length === 0) delete folder.folders;
    if (folder.pages.length === 0) delete folder.pages;

    // attributes 외의 프로퍼티 제거
    for (const key of Object.keys(folder)) {
      //if (key !== 'attributes' && key !== 'folders' && key !== 'pages') {
      if (key !== 'folders' && key !== 'pages') {
        delete folder[key];
      }
    }
  }

  return folders;
}

// 폴더에 속한 페이지만 불러오기 (page_detail 제외)
async function getPages(folderId) {
  const { rows: pages } = await dbPool.query(
    `SELECT * FROM content_rel_pages WHERE folder_id = $1 AND is_deleted = false`,
    [folderId]
  );

  // pages 배열 내 각 항목도 attributes로 감싸기
  return pages.map(page => {
    return { attributes: page };
    //return page
  });
}

/*
// 채널 ID로 전체 구조 반환
async function getStructureByChannel(channelId) {
  const { rows: channels } = await dbPool.query(
    `SELECT * FROM content_rel_channels WHERE id = $1 AND is_deleted = false`,
    [channelId]
  );

  if (channels.length === 0) {
    throw new Error('채널을 찾을 수 없어요');
  }

  // 채널 정보는 반환하지 않고 최상위가 폴더 목록임을 명확히 함
  const folders = await getSubFolders(null, channelId);

  return {
    folders
  };
}

router.get(`/${service_type}/list-directories/:channelId`, async (req, res) => {
  const channelId = parseInt(req.params.channelId);
  if (!channelId) {
    return res.status(400).json({ error: 'channelId를 URL 파라미터로 전달해주세요.' });
  }

  try {
    const structure = await getStructureByChannel(channelId);
    res.json(structure);
  } catch (error) {
    console.error('에러 발생:', error.message);
    res.status(500).json({ error: error.message });
  }
});
*/



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

// 최신 버전 번호 가져오기
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

// latest 버전 조회
router.get(`/${service_type}/get-exe-version`, (req, res) => {
  const exePath = path.join(CONSTANTS.APPLICATION_DIR, "bepsapp.exe");
  if (!fs.existsSync(exePath)) return res.status(404).json({ error: 'File not found' });
  exec(`strings ${exePath} | grep -i "version"`, (err, stdout) => {
    if (err || !stdout.trim()) return res.status(500).json({ error: 'No version info found' });
    res.json({ version: stdout.replace(/[^     res.json({ version: stdout.replace(/[^\x20-\x7E]/g, '').trim() });
  });
});


module.exports = router;
