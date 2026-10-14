"""Build and apply a local workstation configuration plan."""
from __future__ import annotations

from dataclasses import dataclass
import filecmp
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime

from .mcp_config import merge_mcp_config


SKILL_NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
SUPPORTED_CLIENTS = {'kiro', 'claude', 'opencode', 'antigravity', 'codex'}


@dataclass
class PlannedWrite:
    path: Path
    label: str
    source: Path | None = None
    content: bytes | None = None
    link_target: str | None = None
    mode: int = 0o600
    backup: bool = True

    def changed(self):
        if self.path.is_symlink():
            return self.link_target is None or os.readlink(self.path) != self.link_target
        if not self.path.exists():
            return True
        if not self.path.is_file():
            raise ValueError(f'Cannot replace non-file destination: {self.path}')
        if self.link_target is not None:
            return True
        if self.source is not None:
            return not filecmp.cmp(self.source, self.path, shallow=False)
        return self.path.read_bytes() != (self.content or b'')


class DeploymentPlan:
    def __init__(self, home):
        self.home = home.resolve()
        self.directories = {}
        self.writes = []

    def destination(self, relative):
        relative = Path(relative)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Unsafe destination path: {relative}')
        path = self.home / relative
        self.require_inside_home(path)
        return path

    def require_inside_home(self, path):
        parent = path.parent.resolve()
        try:
            parent.relative_to(self.home)
        except ValueError:
            raise ValueError(f'Destination escapes target home: {path}') from None

    def add_directory(self, path, mode):
        try:
            path.resolve().relative_to(self.home)
        except ValueError:
            raise ValueError(f'Destination escapes target home: {path}') from None
        current = path
        while current != self.home and current.is_relative_to(self.home):
            self.directories.setdefault(current, mode)
            current = current.parent

    def add_content(self, path, content, label, mode=0o600, backup=True):
        self.writes.append(PlannedWrite(path, label, content=content, mode=mode, backup=backup))

    def add_source(self, source, path, label, mode=None, backup=True):
        if source.is_symlink():
            self.writes.append(PlannedWrite(path, label, link_target=os.readlink(source), backup=backup))
        else:
            file_mode = stat.S_IMODE(source.stat().st_mode) if mode is None else mode
            self.writes.append(PlannedWrite(path, label, source=source, mode=file_mode, backup=backup))

    def planned_changes(self):
        return [write for write in self.writes if write.changed()]

    def apply(self):
        for directory, mode in sorted(self.directories.items(), key=lambda item: len(item[0].parts)):
            if directory.exists():
                if not directory.is_dir():
                    raise ValueError(f'Cannot create directory over a file: {directory}')
                continue
            directory.mkdir(parents=True, exist_ok=True, mode=mode)
            try:
                directory.chmod(mode)
            except OSError:
                pass

        applied = 0
        for write in self.writes:
            if not write.changed():
                continue
            write.path.parent.mkdir(parents=True, exist_ok=True)
            if write.backup and (write.path.exists() or write.path.is_symlink()):
                backup_existing(write.path)
            replace_file(write)
            applied += 1

        return applied


def backup_existing(path):
    stamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    candidate = path.with_name(f'{path.name}.{stamp}~')
    suffix = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = path.with_name(f'{path.name}.{stamp}.{suffix}~')
        suffix += 1
    if path.is_symlink():
        os.symlink(os.readlink(path), candidate)
    else:
        shutil.copy2(path, candidate)
    return candidate


def replace_file(write):
    write.path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        if write.link_target is not None:
            descriptor, temporary = tempfile.mkstemp(prefix=f'.{write.path.name}.', dir=write.path.parent)
            os.close(descriptor)
            os.unlink(temporary)
            os.symlink(write.link_target, temporary)
            os.replace(temporary, write.path)
            temporary = None
        else:
            descriptor, temporary = tempfile.mkstemp(prefix=f'.{write.path.name}.', dir=write.path.parent)
            os.close(descriptor)
            if write.source is not None:
                shutil.copy2(write.source, temporary)
                os.chmod(temporary, write.mode)
            else:
                with open(temporary, 'wb') as output:
                    output.write(write.content or b'')
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(temporary, write.mode)
            os.replace(temporary, write.path)
            temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
def validate_skills(catalogue, selected):
    if not isinstance(catalogue, dict) or not isinstance(catalogue.get('groups'), list):
        raise ValueError('The skills catalogue must contain a groups list.')
    names = []
    for group in catalogue['groups']:
        if not isinstance(group, dict) or not isinstance(group.get('name'), str) or not isinstance(group.get('skills'), list):
            raise ValueError('Each skill group must contain a name and skills list.')
        names.extend(group['skills'])
    if not names or any(not isinstance(name, str) for name in names) or len(names) != len(set(names)):
        raise ValueError('The skills catalogue is empty or contains duplicate names.')
    if any(not isinstance(name, str) or not SKILL_NAME.fullmatch(name) for name in names):
        raise ValueError('The skills catalogue contains an invalid skill name.')
    required = catalogue.get('required_skills', [])
    if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
        raise ValueError('The skills catalogue has an invalid required_skills list.')
    if len(required) != len(set(required)) or any(name not in names for name in required):
        raise ValueError('The skills catalogue requires a duplicate or unavailable Skill.')
    if any(name not in names for name in selected):
        raise ValueError('Choose skills listed in catalogue/skills.yml.')
    return names


def validate_catalogues(root, skill_catalogue, mcp_catalogue, client_config):
    names = validate_skills(skill_catalogue, [])
    for name in names:
        if not (root / 'skills' / name / 'SKILL.md').is_file():
            raise ValueError(f'Public skill package is missing SKILL.md: {name}')

    servers = mcp_catalogue.get('mcp_servers') if isinstance(mcp_catalogue, dict) else None
    if not isinstance(servers, dict) or not servers:
        raise ValueError('The MCP catalogue must contain at least one server.')
    for name, server in servers.items():
        if not isinstance(name, str) or not SKILL_NAME.fullmatch(name) or not isinstance(server, dict):
            raise ValueError(f'Invalid MCP server entry: {name}')
        if ('url' in server) == ('command' in server):
            raise ValueError(f'MCP server {name} must define either a URL or a command.')
        if 'url' in server and (not isinstance(server['url'], str) or not server['url'].startswith(('https://', 'http://'))):
            raise ValueError(f'MCP server {name} has an invalid URL.')
        if 'command' in server and (not isinstance(server['command'], str) or not server['command']):
            raise ValueError(f'MCP server {name} has an invalid command.')
        if 'args' in server and (not isinstance(server['args'], list) or not all(isinstance(arg, str) for arg in server['args'])):
            raise ValueError(f'MCP server {name} has invalid arguments.')

    skill_paths = client_config.get('client_skill_paths') if isinstance(client_config, dict) else None
    mcp_paths = client_config.get('mcp_client_paths') if isinstance(client_config, dict) else None
    if not isinstance(skill_paths, dict) or not isinstance(mcp_paths, dict) or set(skill_paths) != SUPPORTED_CLIENTS or set(mcp_paths) != SUPPORTED_CLIENTS:
        raise ValueError('Client configuration must define all supported Skills and MCP clients.')
    for key, paths in (('client_skill_paths', skill_paths), ('mcp_client_paths', mcp_paths)):
        for relative in paths.values():
            if not isinstance(relative, str):
                raise ValueError(f'Invalid client configuration path in {key}.')
            path = Path(relative)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError(f'Invalid client configuration path in {key}.')
    return len(names), len(servers)


def add_skill_packages(plan, root, clients, selected, catalogue, client_paths):
    validate_skills(catalogue, selected)
    missing_required = [name for name in catalogue.get('required_skills', []) if name not in selected]
    if missing_required:
        raise ValueError('Mandatory Skills must be selected: ' + ', '.join(missing_required))
    for client in clients:
        if client not in client_paths:
            raise ValueError(f'Unsupported AI client: {client}')
        client_root = plan.destination(client_paths[client])
        plan.add_directory(client_root, 0o755)
        for name in selected:
            source_root = root / 'skills' / name
            if not (source_root / 'SKILL.md').is_file():
                raise ValueError(f'Public skill is missing SKILL.md: {name}')
            destination_root = client_root / name
            package_label = f'Skill {client}/{name}'
            plan.add_directory(destination_root, 0o755)
            for source_dir, directories, files in os.walk(source_root, followlinks=False):
                source_dir = Path(source_dir)
                relative = source_dir.relative_to(source_root)
                target_dir = destination_root / relative
                plan.add_directory(target_dir, 0o755)
                for entry in list(directories):
                    source_entry = source_dir / entry
                    target_entry = target_dir / entry
                    if source_entry.is_symlink():
                        directories.remove(entry)
                        plan.add_source(source_entry, target_entry, package_label)
                    else:
                        plan.add_directory(target_entry, 0o755)
                for entry in files:
                    source_entry = source_dir / entry
                    target_entry = target_dir / entry
                    if source_entry.is_file() or source_entry.is_symlink():
                        plan.add_source(source_entry, target_entry, package_label)


def resolve_mcp_servers(selected, catalogue):
    servers = catalogue.get('mcp_servers', {})
    if any(name not in servers for name in selected):
        raise ValueError('Choose MCP servers listed in catalogue/mcp.yml.')
    resolved = {}
    for name in selected:
        server = dict(servers[name])
        if 'url' in server:
            resolved[name] = server
            continue
        native = shutil.which(name)
        if native:
            server.update(command=native, args=[])
        else:
            runtime = shutil.which(server.get('command', ''))
            if not runtime:
                raise ValueError(f'Install the runtime for {name} before configuring this MCP server.')
            server['command'] = runtime
        resolved[name] = server
    return resolved


def add_mcp_configs(plan, clients, servers, client_paths):
    rendered = []
    for client in clients:
        if client not in client_paths:
            raise ValueError(f'Unsupported AI client: {client}')
        path = plan.destination(client_paths[client])
        if client == 'opencode':
            jsonc = path.with_suffix('.jsonc')
            if jsonc.exists() or jsonc.is_symlink():
                path = jsonc
        existing = path.read_text(encoding='utf-8') if path.exists() else ''
        content = merge_mcp_config(existing, client, servers).encode('utf-8')
        rendered.append((client, path, content))

    for client, path, content in rendered:
        plan.require_inside_home(path)
        if client != 'claude':
            plan.add_directory(path.parent, 0o700)
        plan.add_content(path, content, f'MCP {client}', mode=0o600)


def build_plan(root, home, components, clients, skills, skill_catalogue, mcp_servers, client_config):
    plan = DeploymentPlan(home)
    if 'skills' in components and skills:
        add_skill_packages(plan, root, clients, skills, skill_catalogue, client_config['client_skill_paths'])
    if 'mcp' in components and mcp_servers:
        add_mcp_configs(plan, clients, mcp_servers, client_config['mcp_client_paths'])
    return plan
