const fs = require('fs');
const path = require('path');

const getDirectories = (dirPath) => {
  return fs.readdirSync(dirPath)
    .filter(file => fs.statSync(path.join(dirPath, file)).isDirectory())
    .sort((a, b) => {
      // 이름 앞 3자리 숫자 기준 오름차순 정렬
      const numA = parseInt((a.match(/^(\d{3})_/) || [0, 0])[1], 10);
      const numB = parseInt((b.match(/^(\d{3})_/) || [0, 0])[1], 10);
      return numA - numB;
    });};

const getDirectoryTree = (dirPath) => {
  const buildTree = (currentPath) => {
    const stats = fs.statSync(currentPath);
    const info = { path: currentPath };
    if (stats.isDirectory()) {
      info.children = fs.readdirSync(currentPath)
        .sort((a, b) => {
          // 이름 앞 3자리 숫자 기준 오름차순 정렬
          const numA = parseInt((a.match(/^(\d{3})_/) || [0, 0])[1], 10);
          const numB = parseInt((b.match(/^(\d{3})_/) || [0, 0])[1], 10);
          return numA - numB;
        })
        .map(child => buildTree(path.join(currentPath, child)));
    }
    return info;
  };
  return buildTree(dirPath);
};

module.exports = { getDirectories, getDirectoryTree };
