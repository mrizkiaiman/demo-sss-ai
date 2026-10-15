#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const candidates = [];
if (process.env.SSS_PYTHON) candidates.push(process.env.SSS_PYTHON);
candidates.push(path.join(root, '.venv', 'bin', 'python'));
candidates.push('python3');

let lastError;
for (const python of candidates) {
  if (python !== 'python3' && !fs.existsSync(python)) continue;
  const dependencyCheck = spawnSync(python, ['-c', 'import yaml, json5, tomlkit'], {
    cwd: root,
    stdio: 'ignore',
  });
  if (dependencyCheck.error || dependencyCheck.status !== 0) {
    lastError = dependencyCheck.error || new Error(`${python} is missing SSS Python dependencies`);
    continue;
  }
  const result = spawnSync(python, ['-m', 'cli', ...process.argv.slice(2)], {
    cwd: root,
    stdio: 'inherit',
  });
  if (!result.error) {
    if (result.signal) {
      process.kill(process.pid, result.signal);
    }
    process.exit(result.status === null ? 1 : result.status);
  }
  lastError = result.error;
}

const configured = process.env.SSS_PYTHON ? ` SSS_PYTHON=${process.env.SSS_PYTHON} was not usable.` : '';
console.error(`SSS setup error: Python dependencies are unavailable.${configured} Install requirements.txt in .venv or use a Python 3 installation.`);
if (lastError && process.env.SSS_VERBOSE) console.error(lastError.message);
process.exit(1);
