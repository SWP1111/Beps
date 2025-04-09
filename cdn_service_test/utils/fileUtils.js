const fs = require('fs');
const path = require('path');

const getDirectories = (dirPath) => {
  return fs.readdirSync(dirPath).filter(file => fs.statSync(path.join(dirPath, file)).isDirectory());
};

const getDirectoryTree = (dirPath) => {
  const buildTree = (currentPath) => {
    const stats = fs.statSync(currentPath);
    const info = { path: currentPath };
    if (stats.isDirectory()) {
      info.children = fs.readdirSync(currentPath).map(child => buildTree(path.join(currentPath, child)));
    }
    return info;
  };
  return buildTree(dirPath);
};

module.exports = { getDirectories, getDirectoryTree };
