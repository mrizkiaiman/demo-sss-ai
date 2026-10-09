"""Select local AI clients and preview their configuration before applying."""
import argparse
import curses
import os
import shutil
import signal
from pathlib import Path
import sys
import textwrap

import yaml

from .deploy import build_plan, resolve_mcp_servers, validate_catalogues, validate_skills

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    'kiro': 'Kiro',
    'claude': 'Claude Code',
    'opencode': 'OpenCode',
    'antigravity': 'Antigravity IDE',
    'codex': 'Codex',
}
COMPONENT_LABELS = {'skills': 'Skills', 'mcp': 'MCP servers', 'security': 'Gitleaks and global Git hook'}
BACK = object()


BANNER = """
███████╗  ███████╗  ███████╗
██╔════╝  ██╔════╝  ██╔════╝
███████╗  ███████╗  ███████╗
╚════██║  ╚════██║  ╚════██║
███████║  ███████║  ███████║
╚══════╝  ╚══════╝  ╚══════╝
""".strip('\n')


def group_skills(catalogue):
    return [(group['name'], group['skills']) for group in catalogue['groups']]


def checklist(screen, clients, title='clients to configure', labels=None, groups=None, allow_empty=False, required=None, initial_selected=None, back_label=None):
    labels = LABELS if labels is None else labels
    required = set(required or [])
    curses.curs_set(0)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
    selected = set(required) | (set(initial_selected or []) & set(clients))
    cursor = 0
    message = ''
    offset = 0
    collapsed = set()
    while True:
        rows = []
        if groups is None:
            rows = [(client, [client], False) for client in clients]
        else:
            for index, (name, members) in enumerate(groups):
                rows.append((name, members, True))
                if index not in collapsed:
                    rows.extend((member, [member], False) for member in members)
        display_rows = rows + ([None, (back_label, [], False)] if back_label else [])
        back_cursor = len(rows) + 1 if back_label else None
        cursor = min(cursor, back_cursor if back_label else len(rows))
        screen.erase()
        height, width = screen.getmaxyx()
        compact = width < 64 or height < 24

        def draw(row, text, style=0):
            if row < height - 1 and width > 3:
                screen.addnstr(row, 2, text, width - 3, style)

        accent = curses.color_pair(1) if curses.has_colors() else curses.A_BOLD
        checked = curses.color_pair(2) if curses.has_colors() else curses.A_BOLD
        if compact:
            draw(1, ' SSS / WORKSTATION ', accent | curses.A_REVERSE)
            draw(3, 'Python CLI  /  Skills and MCP', curses.A_DIM)
            heading_row, all_row, list_row = 5, 7, 8
        else:
            for row, line in enumerate(BANNER.splitlines(), 1):
                draw(row, line, curses.A_DIM)
            draw(8, ' WORKSTATION CONFIGURATION ', accent | curses.A_REVERSE)
            draw(10, 'Python CLI  /  Skills and MCP', curses.A_DIM)
            heading_row, all_row, list_row = 12, 14, 15
        visible = max(1, height - 4 - list_row)
        display_cursor = len(rows) + 1 if cursor == back_cursor else cursor - 1 if cursor else 0
        if cursor > 0:
            offset = max(0, min(offset, display_cursor))
            if display_cursor >= offset + visible:
                offset = display_cursor - visible + 1
        end = min(len(display_rows), offset + visible)
        draw(heading_row, f'Select {title}', curses.A_BOLD)
        all_enabled = len(selected) == len(clients)
        draw(all_row, f"{'>' if cursor == 0 else ' '} {'●' if all_enabled else '○'} Select all ({len(selected)}/{len(clients)})", accent | curses.A_BOLD if cursor == 0 else checked if all_enabled else 0)
        for index in range(offset, end):
            row = display_rows[index]
            if row is None:
                continue
            name, members, is_group = row
            active = index + 1 == cursor if index < len(rows) else cursor == back_cursor
            if back_label and index == len(rows) + 1:
                draw(list_row + index - offset, f"{'>' if active else ' '} ↩ {name}", accent | curses.A_BOLD if active else 0)
                continue
            count = len(selected.intersection(members))
            mark = '●' if count == len(members) else '◐' if count else '○'
            group_index = next((number for number, group in enumerate(groups or []) if group[1] is members), None)
            prefix = ('▸' if group_index in collapsed else '▾') if is_group else ' '
            label = f'{name} ({count}/{len(members)})' if is_group else labels.get(name, name)
            if not is_group and name in required:
                label += ' [MANDATORY]'
            line = f"{'>' if active else ' '} {mark} {prefix} {label}"
            draw(list_row + index - offset, line, (accent | curses.A_BOLD) if active else checked if count else curses.A_BOLD if is_group else 0)
        draw(height - 4, '─' * min(width - 5, 60), curses.A_DIM)
        controls = '↑↓ move  ←→ groups  Space toggle  Enter continue  q cancel' if groups else '↑↓ move  Space toggle  Enter continue  q cancel'
        if back_label:
            controls = controls.replace('  q cancel', '  b back  q cancel')
        if width < 48:
            controls = '↑↓ move  Space select  Enter  q cancel'
            if back_label:
                controls = controls.replace('  q cancel', '  b back  q cancel')
        draw(height - 3, controls, curses.A_DIM)
        draw(height - 2, message or (f'Rows {offset + 1}-{end} of {len(rows)}' if len(rows) > visible else ''), accent)
        screen.refresh()
        key = screen.getch()
        if key in (ord('q'), 27):
            return None
        if back_label and key in (ord('b'), ord('B')):
            return BACK
        if key == 3:
            raise KeyboardInterrupt
        if key in (curses.KEY_UP, ord('k')):
            cursor = (cursor - 1) % (len(rows) + 2 if back_label else len(rows) + 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            cursor = (cursor + 1) % (len(rows) + 2 if back_label else len(rows) + 1)
        elif key == ord(' '):
            if cursor == 0:
                if len(selected) == len(clients):
                    selected = set(required)
                    message = 'Required items remain selected.' if required else ''
                else:
                    selected = set(clients)
                    message = ''
            elif not back_label or cursor != len(rows) + 1:
                members = set(rows[cursor - 1][1])
                if members:
                    if members <= selected:
                        selected.difference_update(members - required)
                        message = 'Mandatory: ' + ', '.join(sorted(members & required)) if members & required else ''
                    else:
                        selected.update(members)
                        message = ''
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT) and cursor and cursor <= len(rows) and rows[cursor - 1][2]:
            members = rows[cursor - 1][1]
            index = next(number for number, group in enumerate(groups) if group[1] is members)
            collapsed.add(index) if key == curses.KEY_LEFT else collapsed.discard(index)
        elif key in (10, 13, curses.KEY_ENTER):
            if back_label and cursor == len(rows) + 1:
                return BACK
            if selected or allow_empty:
                return [client for client in clients if client in selected]
            message = 'Select at least one item to continue.'


def select_options(clients, title, labels, groups=None, allow_empty=False, required=None, initial_selected=None, back_label=None):
    required = set(required or [])
    if sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM', 'dumb') != 'dumb':
        return curses.wrapper(checklist, clients, title, labels, groups, allow_empty, required, initial_selected, back_label)
    initial_selected = set(initial_selected or []) | required
    empty_hint = ', '.join(client for client in clients if client in initial_selected) if initial_selected else 'none' if allow_empty else 'cancel'
    print(f'Select {title}. Enter numbers separated by commas or spaces, all, or q to cancel. Press Enter to select {empty_hint}.')
    number = 0
    for heading, members in groups if groups is not None else [(None, clients)]:
        if heading:
            print(f'\n  {heading}')
        for client in members:
            number += 1
            label = labels.get(client, client)
            if client in required:
                label += ' [MANDATORY]'
            print(f'  {number}. {label}')
    if back_label:
        print()
        print(f'  b. ↩ {back_label}')
    while True:
        answer = input('Selection: ').strip().lower()
        if answer == 'q':
            return None
        if answer == 'b' and back_label:
            return BACK
        if answer == 'all':
            return clients
        if not answer:
            return [client for client in clients if client in initial_selected]
        tokens = answer.replace(',', ' ').split()
        if tokens and all(token.isascii() and token.isdigit() and 1 <= int(token) <= len(clients) for token in tokens):
            selected = {clients[int(token) - 1] for token in tokens}
            return [client for client in clients if client in required or client in selected]
        print('Invalid selection. Choose at least one listed number, all, or q.')


def select_clients(clients):
    return select_options(clients, 'clients to configure', LABELS, back_label='Back')


def print_change_recap(target_home, clients, skills, groups, servers, security=False, preview_only=False):
    width = max(20, min(88, shutil.get_terminal_size((88, 24)).columns - 2))
    content_width = width - 4
    color = sys.stdout.isatty() and os.environ.get('TERM', 'dumb') != 'dumb' and 'NO_COLOR' not in os.environ
    unicode_borders = os.environ.get('TERM', 'dumb') != 'dumb'
    top, bottom, side, rule = ('┌', '└', '│', '─') if unicode_borders else ('+', '+', '|', '-')
    top_end, bottom_end = ('┐', '┘') if unicode_borders else ('+', '+')
    lines = ['SSS / CHANGE RECAP', 'PREVIEW COMPLETE', '', f'Target home: {target_home}']
    if clients:
        lines.append('Clients: ' + ', '.join(LABELS.get(client, client) for client in clients))
    if skills:
        lines.extend(['', f'SKILLS / {len(skills)} selected'])
        for group_name, group_members in groups:
            selected = [name for name in group_members if name in skills]
            if selected:
                lines.extend([f'  {group_name}', '    ' + ', '.join(selected)])
    if servers:
        lines.extend(['', f'MCP / {len(servers)} selected', '  ' + ', '.join(servers)])
    if security:
        lines.extend(['', 'SECURITY', '  Shared Gitleaks rules and global Git hook', f'  Rules: {target_home / ".config/company-ai/gitleaks.toml"}', '  Existing hook preserved and chained when present'])
    if not skills and not servers and not security:
        lines.extend(['', 'No skills, MCP servers, or security changes selected.'])
    lines.extend(['', 'Preview only. No changes applied.' if preview_only else 'Review the selections before applying.'])
    print('\n' + top + rule * (width - 2) + top_end)
    for index, line in enumerate(lines):
        indent = line[:len(line) - len(line.lstrip())]
        for part in textwrap.wrap(line, content_width, subsequent_indent=indent, break_on_hyphens=False) or ['']:
            text = part.ljust(content_width)
            if color and index < 2:
                text = f'\033[1;{36 if index == 0 else 32}m{text}\033[0m'
            print(f'{side} {text} {side}')
    print(bottom + rule * (width - 2) + bottom_end)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', action='store_true', help='Validate catalogues and public Skill packages, then exit.')
    parser.add_argument('--check', action='store_true', help='Preview only, without asking to apply.')
    parser.add_argument('--verbose', action='store_true', help='List planned file paths without showing their contents.')
    parser.add_argument('--target-home', type=Path, default=Path.home(), help='Absolute installation home. Defaults to the current user home.')
    args = parser.parse_args()
    target_home = args.target_home.expanduser()
    if not target_home.is_absolute():
        parser.error('--target-home must be an absolute path')
    target_home = target_home.resolve()
    try:
        client_config = yaml.safe_load((ROOT / 'config/clients.yml').read_text(encoding='utf-8'))
        skill_data = yaml.safe_load((ROOT / 'catalogue/skills.yml').read_text(encoding='utf-8'))
        skill_catalogue = skill_data.get('skill_catalogue') if isinstance(skill_data, dict) else None
        mcp_catalogue = yaml.safe_load((ROOT / 'catalogue/mcp.yml').read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        parser.error(f'Cannot load project configuration: {error}')
    try:
        validate_skills(skill_catalogue, [])
        required_skills = skill_catalogue.get('required_skills', [])
    except (TypeError, ValueError) as error:
        parser.error(f'Cannot read catalogue/skills.yml: {error}')
    if args.validate:
        try:
            skill_count, mcp_count = validate_catalogues(ROOT, skill_catalogue, mcp_catalogue, client_config)
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
            parser.error(str(error))
        print(f'Catalogues valid: {skill_count} Skills, {mcp_count} MCP servers, {len(client_config["client_skill_paths"])} clients.')
        return 0
    print(BANNER)
    print('\nSSS  /  Workstation configuration\n')
    required_components = ['skills'] if required_skills else []
    components = []
    while True:
        components = select_options(
            list(COMPONENT_LABELS),
            'components to configure',
            COMPONENT_LABELS,
            required=required_components,
            initial_selected=components,
        )
        if not components:
            print('Cancelled. No changes were made.')
            return 0
        clients = []
        if any(component in components for component in ['skills', 'mcp']):
            clients = select_clients(list(client_config['client_skill_paths']))
            if clients is BACK:
                continue
            if not clients:
                print('Cancelled. No changes were made.')
                return 0
        break
    skills = []
    groups = []
    selected_mcp = []
    if 'skills' in components:
        groups = group_skills(skill_catalogue)
        available_skills = [name for _, members in groups for name in members]
        skills = select_options(available_skills, 'skills to install', {}, groups, allow_empty=True, required=required_skills)
        if skills is None:
            print('Cancelled. No changes were made.')
            return 0
    if 'mcp' in components:
        selected_mcp = select_options(list(mcp_catalogue['mcp_servers']), 'MCP servers to configure', {}, allow_empty=True)
        if selected_mcp is None:
            print('Cancelled. No changes were made.')
            return 0
    try:
        servers = resolve_mcp_servers(selected_mcp, mcp_catalogue)
        plan = build_plan(ROOT, target_home, components, clients, skills, skill_catalogue, servers, client_config)
        changes = plan.planned_changes()
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        parser.error(str(error))
    print('\nInstallation targets:')
    if 'security' in components:
        print(f'  Global Gitleaks rules: {target_home / client_config["security_config_dir"] / "gitleaks.toml"}')
        print(f'  Global Git hook: existing core.hooksPath, or {target_home / client_config["security_hooks_dir"]}')
        print('  Existing pre-commit hook, if any: preserved and chained')
    for client in clients:
        if 'skills' in components:
            print(f"  {LABELS.get(client, client)} skills: {target_home / client_config['client_skill_paths'][client]}")
        if 'mcp' in components:
            path = target_home / client_config['mcp_client_paths'][client]
            if client == 'opencode' and path.with_suffix('.jsonc').is_file():
                path = path.with_suffix('.jsonc')
            print(f"  {LABELS.get(client, client)} MCP: {path}")
    if skills:
        print('Skills: ' + ', '.join(skills))
    for name in selected_mcp:
        definition = servers[name]
        if 'url' in definition:
            print(f"MCP {name}: remote OAuth server at {definition['url']}")
        else:
            print(f"MCP {name}: {definition['command']} {' '.join(definition.get('args', []))}")
    print_change_recap(target_home, clients, skills, groups, selected_mcp, 'security' in components, args.check)
    print(f'\nPlanned file changes: {len(changes)}')
    if plan.hooks_path is not None:
        print(f'Global Git hooks path will be set to: {plan.hooks_path}')
    if args.verbose:
        for write in changes:
            print(f'  {write.label}: {write.path}')
    if not changes and plan.hooks_path is None:
        print('No changes are needed.')
        return 0
    if args.check:
        return 0
    if input('\nApply these changes? [y/N]: ').strip().lower() not in ['y', 'yes']:
        print('No changes applied.')
        return 0
    try:
        applied = plan.apply()
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(f'Apply failed: {error}')
    print(f'\nApply completed. Updated {applied} file(s).', flush=True)
    if plan.hooks_path is not None:
        print(f'Configured global Git hooks path: {plan.hooks_path}', flush=True)
    return 0


def cancel_setup(signum, frame):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    raise KeyboardInterrupt


def cli():
    signal.signal(signal.SIGINT, cancel_setup)
    try:
        return main()
    except (EOFError, KeyboardInterrupt):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        print('\nSetup cancelled.', flush=True)
        return 130


if __name__ == '__main__':
    raise SystemExit(cli())
