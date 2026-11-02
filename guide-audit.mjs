import fs from 'node:fs';
import path from 'node:path';

const root = process.argv[2];
const { pathToFileURL } = await import('node:url');
const { explainProblem } = await import(pathToFileURL(path.join(root, 'app/student/user-guidance.mjs')).href);
const GENERIC = '请重新双击安装包里的启动文件，在新打开的控制台中再操作一次';
const files = [];
(function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === 'runtime') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (/\.(mjs|js)$/.test(entry.name)) files.push(full);
  }
})(path.join(root, 'app'));

const messages = new Set();
for (const file of files) {
  const text = fs.readFileSync(file, 'utf8');
  for (const match of text.matchAll(/(?:throw new Error\(|new Error\(|reject\(new Error\(|error:\s*)'([^'\\]{4,60})'/g)) {
    const value = match[1];
    if (!/[\u4e00-\u9fa5]/.test(value)) continue;
    messages.add(value);
  }
}
const gaps = [];
for (const message of messages) {
  const answer = explainProblem(message);
  if (answer.startsWith(GENERIC)) gaps.push(message);
}
console.log('提取消息数:', messages.size, ' 掉进兜底:', gaps.length);
for (const gap of gaps.sort()) console.log('  -', gap);
