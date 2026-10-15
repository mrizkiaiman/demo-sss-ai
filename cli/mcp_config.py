"""Render MCP entries for each supported client without exposing config values."""
from dataclasses import dataclass, field
import json

import json5
import tomlkit


class MCPConfigError(ValueError):
    pass


@dataclass
class MCPMergeResult:
    """Safe merge output plus names affected by the explicit conflict policy."""

    content: str
    added: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)

    @property
    def changed(self):
        return bool(self.added or self.updated)


def _new_entry(client):
    return tomlkit.table() if client == 'codex' else {}


def _apply_server(entry, client, server):
    if 'url' in server:
        for stale in ['command', 'args', 'env', 'environment', 'startup_timeout_sec', 'httpUrl', 'serverUrl']:
            entry.pop(stale, None)
        if client == 'claude':
            entry.update({'type': 'http', 'url': server['url']})
        elif client == 'opencode':
            entry.update({'type': 'remote', 'url': server['url'], 'enabled': True})
        elif client == 'antigravity':
            entry.update({'serverUrl': server['url'], 'disabled': False})
            entry.pop('url', None)
        else:
            entry.update({'url': server['url']})
            if client == 'kiro':
                entry.pop('type', None)
                entry['disabled'] = False
            elif client == 'codex':
                entry.pop('type', None)
                entry['enabled'] = True
        return

    for stale in ['url', 'serverUrl', 'httpUrl']:
        entry.pop(stale, None)
    entry['command'] = [server['command'], *server.get('args', [])] if client == 'opencode' else server['command']
    if client == 'opencode':
        entry.pop('args', None)
        entry.update({'type': 'local', 'enabled': True})
    else:
        entry['args'] = server.get('args', [])
        if client == 'claude':
            entry['type'] = 'stdio'
        elif client == 'kiro':
            entry['disabled'] = False
        elif client == 'codex':
            entry.pop('type', None)
            entry['enabled'] = True
            entry['startup_timeout_sec'] = server.get('startup_timeout_sec', 60)
    entry.pop('environment', None)
    entry.pop('env', None)
    if server.get('env'):
        entry.setdefault('environment' if client == 'opencode' else 'env', {}).update(server['env'])


def merge_mcp_config(text, client, servers, allow_updates=False):
    """Merge only missing entries unless the caller explicitly allows updates."""
    try:
        data = tomlkit.parse(text) if client == 'codex' else json5.loads(text, allow_duplicate_keys=False) if text.strip() else {}
        key = 'mcp_servers' if client == 'codex' else 'mcp' if client == 'opencode' else 'mcpServers'
        section = data.setdefault(key, _new_entry(client))
        if not hasattr(section, 'items'):
            raise ValueError('MCP server section must be an object')

        added = []
        skipped = []
        updated = []
        for name, server in servers.items():
            if name in section:
                if not allow_updates:
                    skipped.append(name)
                    continue
                entry = section[name]
                if not hasattr(entry, 'items'):
                    raise ValueError('Managed MCP entry must be an object')
                _apply_server(entry, client, server)
                updated.append(name)
                continue
            entry = section.setdefault(name, _new_entry(client))
            if not hasattr(entry, 'items'):
                raise ValueError('Managed MCP entry must be an object')
            _apply_server(entry, client, server)
            added.append(name)

        if not added and not updated:
            return MCPMergeResult(text, skipped=skipped)
        content = tomlkit.dumps(data) if client == 'codex' else json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        return MCPMergeResult(content, added=added, skipped=skipped, updated=updated)
    except Exception as error:
        # Keep secrets and existing client config out of terminal output.
        raise MCPConfigError(f'Cannot merge {client} MCP configuration ({type(error).__name__}). Existing configuration was not replaced.') from None
