"""Build and apply a local workstation configuration plan."""
from __future__ import annotations

from dataclasses import dataclass
import filecmp
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from datetime import datetime

from .mcp_config import merge_mcp_config


SKILL_NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
SUPPORTED_CLIENTS = {'kiro', 'claude', 'opencode', 'antigravity', 'codex'}
SUPPORTED_OS = {'macos', 'linux', 'windows-wsl2', 'unknown'}
SUPPORTED_COMPLEXITY = {'low', 'medium', 'high', 'unknown', 'not specified'}
SUPPORTED_MCP_FORMATS = {'json', 'json5', 'toml'}


@dataclass
class PlannedWrite:
    path: Path
    label: str
    source: Path | None = None
    content: bytes | None = None
    link_target: str | None = None
    mode: int = 0o600
    backup: bool = True
    action: str = 'create'

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

    @property
    def display_action(self):
        return 'replace' if self.path.exists() or self.path.is_symlink() else self.action


class DeploymentPlan:
    def __init__(self, home):
        self.home = Path(home).expanduser().resolve()
        self.directories = {}
        self.writes = []
        self.warnings = []

    def destination(self, relative):
        relative = Path(relative)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Unsafe destination path: {relative}')
        path = self.home / relative
        self.require_inside_home(path)
        return path

    def require_inside_home(self, path):
        path = Path(path)
        parent = path.parent.resolve()
        try:
            parent.relative_to(self.home)
        except ValueError:
            raise ValueError(f'Destination escapes target home: {path}') from None

    def add_directory(self, path, mode):
        path = Path(path)
        try:
            path.resolve().relative_to(self.home)
        except ValueError:
            raise ValueError(f'Destination escapes target home: {path}') from None
        current = path
        while current != self.home and current.is_relative_to(self.home):
            self.directories.setdefault(current, mode)
            current = current.parent

    def add_content(self, path, content, label, mode=0o600, backup=True, action='create'):
        self.require_inside_home(path)
        self.writes.append(PlannedWrite(path, label, content=content, mode=mode, backup=backup, action=action))

    def add_source(self, source, path, label, mode=None, backup=True, action='create'):
        self.require_inside_home(path)
        if source.is_symlink():
            self.writes.append(PlannedWrite(path, label, link_target=os.readlink(source), backup=backup, action=action))
        else:
            file_mode = stat.S_IMODE(source.stat().st_mode) if mode is None else mode
            self.writes.append(PlannedWrite(path, label, source=source, mode=file_mode, backup=backup, action=action))

    def warn(self, message):
        self.warnings.append(message)

    def planned_changes(self):
        return [write for write in self.writes if write.changed()]

    def apply(self):
        for directory, mode in sorted(self.directories.items(), key=lambda item: len(item[0].parts)):
            if directory.is_symlink() and not directory.exists():
                directory = directory.resolve()
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
def _validate_metadata(metadata, label, complexity_key):
    if not isinstance(metadata, dict):
        raise ValueError(f'{label} metadata must be an object.')
    operating_systems = metadata.get('os_compatibility')
    if not isinstance(operating_systems, list) or not operating_systems or any(value not in SUPPORTED_OS for value in operating_systems):
        raise ValueError(f'{label} metadata has invalid os_compatibility.')
    complexity = metadata.get(complexity_key)
    if not isinstance(complexity, str) or complexity not in SUPPORTED_COMPLEXITY:
        raise ValueError(f'{label} metadata has invalid {complexity_key}.')
    note = metadata.get('note')
    if not isinstance(note, str) or not note.strip():
        raise ValueError(f'{label} metadata must contain a non-empty note.')


def _validate_catalogue_metadata(catalogue, names, label):
    if not isinstance(catalogue, dict):
        raise ValueError(f'{label} catalogue must be an object.')
    presentation = catalogue.get('presentation')
    if presentation is not None:
        _validate_metadata(presentation, f'{label} presentation', 'installation_complexity')
    overrides = catalogue.get('metadata', {})
    if overrides is None:
        return
    if not isinstance(overrides, dict) or any(name not in names for name in overrides):
        raise ValueError(f'{label} metadata must map known entries to metadata.')
    for name, metadata in overrides.items():
        _validate_metadata(metadata, f'{label} entry {name}', 'installation_complexity')


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
    _validate_catalogue_metadata(catalogue, names, 'Skills')
    return names


def validate_catalogues(root, skill_catalogue, mcp_catalogue, client_config):
    names = validate_skills(skill_catalogue, [])
    for name in names:
        if not (root / 'skills' / name / 'SKILL.md').is_file():
            raise ValueError(f'Public skill package is missing SKILL.md: {name}')

    if not isinstance(mcp_catalogue, dict):
        raise ValueError('The MCP catalogue must be an object.')
    servers = mcp_catalogue.get('mcp_servers')
    if not isinstance(servers, dict) or not servers:
        raise ValueError('The MCP catalogue must contain at least one server.')
    _validate_catalogue_metadata(mcp_catalogue, list(servers), 'MCP')
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

    if not isinstance(client_config, dict):
        raise ValueError('Client configuration must be an object.')
    skill_paths = client_config.get('client_skill_paths')
    mcp_paths = client_config.get('mcp_client_paths')
    capabilities = client_config.get('client_capabilities')
    metadata = client_config.get('client_metadata')
    if not isinstance(skill_paths, dict) or not isinstance(mcp_paths, dict) or set(skill_paths) != SUPPORTED_CLIENTS or set(mcp_paths) != SUPPORTED_CLIENTS:
        raise ValueError('Client configuration must define all supported Skills and MCP clients.')
    if not isinstance(capabilities, dict) or set(capabilities) != SUPPORTED_CLIENTS:
        raise ValueError('Client configuration must define capabilities for all supported clients.')
    if not isinstance(metadata, dict) or set(metadata) != SUPPORTED_CLIENTS:
        raise ValueError('Client configuration must define metadata for all supported clients.')
    for client in SUPPORTED_CLIENTS:
        client_caps = capabilities[client]
        if not isinstance(client_caps, dict) or set(client_caps) != {'skills', 'mcp', 'mcp_format'}:
            raise ValueError(f'Invalid capability matrix for client: {client}.')
        for component in ('skills', 'mcp'):
            component_caps = client_caps[component]
            if not isinstance(component_caps, dict) or set(component_caps) != {'global', 'project'} or any(not isinstance(value, bool) for value in component_caps.values()):
                raise ValueError(f'Invalid {component} capability matrix for client: {client}.')
        if client_caps['mcp_format'] not in SUPPORTED_MCP_FORMATS:
            raise ValueError(f'Invalid native MCP format for client: {client}.')
        _validate_metadata(metadata[client], f'Client {client}', 'complexity')
    for key, paths in (('client_skill_paths', skill_paths), ('mcp_client_paths', mcp_paths)):
        for client, relative in paths.items():
            if not isinstance(relative, str):
                raise ValueError(f'Invalid client configuration path in {key}.')
            path = Path(relative)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError(f'Invalid client configuration path in {key}.')
            component = 'skills' if key == 'client_skill_paths' else 'mcp'
            if not relative and any(capabilities[client][component].values()):
                raise ValueError(f'{client} advertises {component} capability without a native path.')
    return len(names), len(servers)


def validate_scope_capabilities(scope, components, clients, client_config):
    capabilities = client_config.get('client_capabilities', {})
    unsupported = []
    for client in clients:
        client_caps = capabilities.get(client, {})
        for component in components:
            if component == 'guardrails':
                continue
            if not client_caps.get(component, {}).get(scope, False):
                unsupported.append(f'{client} {component}')
    if unsupported:
        raise ValueError(f'{scope.title()} scope is not supported for: {", ".join(unsupported)}.')


def catalogue_metadata(catalogue, name):
    presentation = (catalogue.get('presentation') or {}) if isinstance(catalogue, dict) else {}
    overrides = (catalogue.get('metadata') or {}) if isinstance(catalogue, dict) else {}
    metadata = overrides.get(name, {})
    return {**presentation, **metadata}


def add_skill_packages(plan, root, clients, selected, catalogue, client_paths, allow_updates=False):
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
            existing_package = destination_root.exists() or destination_root.is_symlink()
            if existing_package and not allow_updates:
                plan.warn(f'Skipped existing {package_label} at {destination_root} (use --update or --force).')
                continue
            if existing_package and not destination_root.is_dir():
                raise ValueError(f'Cannot update non-directory Skill destination: {destination_root}')
            action = 'update' if existing_package else 'create'
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
                        plan.add_source(source_entry, target_entry, package_label, action=action)
                    else:
                        plan.add_directory(target_entry, 0o755)
                for entry in files:
                    source_entry = source_dir / entry
                    target_entry = target_dir / entry
                    if source_entry.is_file() or source_entry.is_symlink():
                        plan.add_source(source_entry, target_entry, package_label, action=action)


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


def add_mcp_configs(plan, clients, servers, client_paths, allow_updates=False):
    for client in clients:
        if client not in client_paths:
            raise ValueError(f'Unsupported AI client: {client}')
        path = plan.destination(client_paths[client])
        if client == 'opencode':
            jsonc = path.with_suffix('.jsonc')
            if jsonc.exists() or jsonc.is_symlink():
                path = jsonc
        plan.require_inside_home(path)
        existing = path.read_text(encoding='utf-8') if path.exists() or path.is_symlink() else ''
        result = merge_mcp_config(existing, client, servers, allow_updates=allow_updates)
        for name in result.skipped:
            plan.warn(f'Skipped existing MCP {client}/{name} at {path} (use --update or --force).')
        if not result.changed:
            continue
        if client != 'claude':
            plan.add_directory(path.parent, 0o700)
        existing_destination = path.exists() or path.is_symlink()
        plan.add_content(
            path,
            result.content.encode('utf-8'),
            f'MCP {client}',
            mode=0o600,
            backup=existing_destination,
            action='update' if existing_destination else 'create',
        )


def add_agent_guardrails(plan, root, scope, allow_updates=False):
    if scope != 'project':
        raise ValueError('AI guardrails require --scope project so AGENTS.md stays local to the selected repository.')
    source = root / 'templates' / 'AGENTS.md'
    if not source.is_file():
        raise ValueError(f'Guardrail template is missing: {source}')
    path = plan.destination('AGENTS.md')
    existing = path.exists() or path.is_symlink()
    if existing and path.is_symlink():
        raise ValueError(f'Cannot replace symlink guardrail destination: {path}')
    if existing and not path.is_file():
        raise ValueError(f'Cannot replace non-file guardrail destination: {path}')
    if existing and not allow_updates:
        plan.warn(f'Skipped existing AI guardrails at {path} (use --update or --force).')
        return
    plan.add_content(
        path,
        source.read_bytes(),
        'AI guardrails / AGENTS.md',
        mode=0o644,
        backup=existing,
        action='update' if existing else 'create',
    )


def build_plan(root, home, components, clients, skills, skill_catalogue, mcp_servers, client_config, allow_updates=False, scope=None):
    plan = DeploymentPlan(home)
    if 'guardrails' in components:
        add_agent_guardrails(plan, root, scope, allow_updates=allow_updates)
    if 'skills' in components and skills:
        add_skill_packages(plan, root, clients, skills, skill_catalogue, client_config['client_skill_paths'], allow_updates=allow_updates)
    if 'mcp' in components and mcp_servers:
        add_mcp_configs(plan, clients, mcp_servers, client_config['mcp_client_paths'], allow_updates=allow_updates)
    return plan
