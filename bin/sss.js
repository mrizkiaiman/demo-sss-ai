#!/usr/bin/env node

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const packageVersion = packageJson.version;
const projectCwd = process.cwd();
const requestedArgs = process.argv.slice(2);
const setupRequested = requestedArgs[0] === 'setup';
const cliArgs = setupRequested ? requestedArgs.slice(1) : requestedArgs;

function venvPython(venvDirectory) {
  return process.platform === 'win32'
    ? path.join(venvDirectory, 'Scripts', 'python.exe')
    : path.join(venvDirectory, 'bin', 'python');
}

function cachedVenvDirectory() {
  const cacheRoot = process.env.SSS_CACHE_DIR || process.env.XDG_CACHE_HOME || path.join(os.homedir(), '.cache');
  return path.join(cacheRoot, 'sss-ai-cli', packageVersion, 'venv');
}

function isImportReady(python) {
  const result = spawnSync(python, ['-c', 'import yaml, json5, tomlkit'], {
    cwd: root,
    stdio: 'ignore',
  });
  return !result.error && result.status === 0;
}

function isUsable(python) {
  if (python.includes(path.sep) && !fs.existsSync(python)) return false;
  return true;
}

function run(python, args) {
  const result = spawnSync(python, args, {
    cwd: projectCwd,
    stdio: 'inherit',
  });
  if (result.error) {
    console.error(`SSS setup error: ${result.error.message}`);
    process.exit(1);
  }
  if (result.signal) process.kill(process.pid, result.signal);
  if (result.status !== 0) process.exit(result.status === null ? 1 : result.status);
}

function basePython() {
  const candidates = [
    process.env.SSS_PYTHON,
    process.platform === 'win32' ? 'python' : 'python3',
    'python',
  ].filter(Boolean);
  return candidates.find(isUsable);
}

function bootstrapPython() {
  const readyCandidates = [
    process.env.SSS_PYTHON,
    venvPython(cachedVenvDirectory()),
    venvPython(path.join(root, '.venv')),
    process.platform === 'win32' ? 'python' : 'python3',
    'python',
  ].filter(Boolean);
  const ready = readyCandidates.find((python) => isUsable(python) && isImportReady(python));
  if (ready) return ready;

  const base = basePython();
  if (!base) {
    console.error('SSS setup error: Python 3 is required. Install Python 3 and run `npx sss-ai-cli setup` again.');
    process.exit(1);
  }

  const venvDirectory = cachedVenvDirectory();
  const python = venvPython(venvDirectory);
  if (!fs.existsSync(python)) {
    console.log(`Creating cached Python environment at ${venvDirectory}`);
    fs.mkdirSync(path.dirname(venvDirectory), { recursive: true });
    run(base, ['-m', 'venv', venvDirectory]);
  }
  if (!isImportReady(python)) {
    console.log('Installing pinned Python dependencies for SSS');
    run(python, ['-m', 'pip', 'install', '-r', path.join(root, 'requirements.txt')]);
  }
  if (!isImportReady(python)) {
    console.error('SSS setup error: Python dependencies could not be installed.');
    process.exit(1);
  }
  return python;
}

const python = bootstrapPython();
run(python, ['-m', 'cli', ...cliArgs]);
