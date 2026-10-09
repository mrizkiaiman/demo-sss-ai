"""Render MCP entries for each supported client without exposing config values."""
import json

import json5
import tomlkit


class MCPConfigError(ValueError):
    pass


def merge_mcp_config(text, client, servers):
    try:
        data = tomlkit.parse(text) if client == 'codex' else json5.loads(text, allow_duplicate_keys=False) if text.strip() else {}
        key = 'mcp_servers' if client == 'codex' else 'mcp' if client == 'opencode' else 'mcpServers'
        section = data.setdefault(key, tomlkit.table() if client == 'codex' else {})
        if not hasattr(section, 'items'):
            raise ValueError('MCP server section must be an object')
        for name, server in servers.items():
            entry = section.setdefault(name, tomlkit.table() if client == 'codex' else {})
            if not hasattr(entry, 'items'):
                raise ValueError('Managed MCP entry must be an object')
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
            else:
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
                if server.get('env'):
                    entry.setdefault('environment' if client == 'opencode' else 'env', {}).update(server['env'])
        return tomlkit.dumps(data) if client == 'codex' else json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    except Exception as error:
        # Keep secrets and existing client config out of terminal output.
        raise MCPConfigError(f'Cannot merge {client} MCP configuration ({type(error).__name__}). Existing configuration was not replaced.') from None
