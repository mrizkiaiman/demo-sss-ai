#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const projectCwd = process.cwd();
const requestedArgs = process.argv.slice(2);
const cliArgs = requestedArgs[0] === 'setup' ? requestedArgs.slice(1) : requestedArgs;
const vendor = path.join(root, 'vendor');
const pythonEnv = {
  ...process.env,
  PYTHONPATH: [root, vendor, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
};
const candidates = [
  process.env.SSS_PYTHON,
  process.platform === 'win32' ? 'python' : 'python3',
  'python',
].filter(Boolean);

function isUsable(python) {
  if (python.includes(path.sep) && !fs.existsSync(python)) return false;
  return true;
}

function hasDependencies(python) {
  const result = spawnSync(python, ['-c', 'import yaml, json5, tomlkit'], {
    cwd: root,
    env: pythonEnv,
    stdio: 'ignore',
  });
  return !result.error && result.status === 0;
}

function run(python) {
  const result = spawnSync(python, ['-m', 'cli', ...cliArgs], {
    cwd: projectCwd,
    env: pythonEnv,
    stdio: 'inherit',
  });
  if (result.error) {
    console.error(`SSS setup error: ${result.error.message}`);
    process.exit(1);
  }
  if (result.signal) process.kill(process.pid, result.signal);
  process.exit(result.status === null ? 1 : result.status);
}

const python = candidates.find((candidate) => isUsable(candidate) && hasDependencies(candidate));
if (!python) {
  console.error('SSS setup error: Python 3 is required. The npm package includes its Python dependencies, so no venv or pip install is needed.');
  console.error('Install Python 3 or set SSS_PYTHON to a Python 3 executable.');
  process.exit(1);
}

run(python);
