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

from .deploy import (
    build_plan,
    catalogue_metadata,
    resolve_mcp_servers,
    validate_catalogues,
    validate_scope_capabilities,
    validate_skills,
)

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    'kiro': 'Kiro',
    'claude': 'Claude Code',
    'opencode': 'OpenCode',
    'antigravity': 'Antigravity IDE',
    'codex': 'Codex',
}
COMPONENT_LABELS = {
    'skills': 'Skills',
    'mcp': 'MCP servers',
    'guardrails': 'AI guardrails',
}
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


def metadata_summary(metadata, complexity_key='installation_complexity'):
    systems = ', '.join(metadata.get('os_compatibility', ['unknown']))
    complexity = metadata.get(complexity_key, 'not specified')
    return f'OS: {systems}; complexity: {complexity}'


def _compact_metadata_label(metadata):
    os_labels = {'macos': 'macOS', 'linux': 'Linux', 'windows-wsl2': 'Windows/WSL2'}
    systems = ' · '.join(os_labels.get(system, system) for system in metadata.get('os_compatibility', ['unknown']))
    complexity = metadata.get('installation_complexity', metadata.get('complexity', 'not specified'))
    return f'Setup {str(complexity).lower()}  ·  {systems}'


def client_labels(client_config, scope):
    labels = {}
    capabilities = client_config.get('client_capabilities', {})
    metadata = client_config.get('client_metadata', {})
    for client in client_config.get('client_skill_paths', {}):
        client_caps = capabilities.get(client, {})
        client_meta = metadata.get(client, {})
        skill_mark = '✓' if client_caps.get('skills', {}).get(scope, False) else '—'
        mcp_mark = '✓' if client_caps.get('mcp', {}).get(scope, False) else '—'
        labels[client] = (
            f'{LABELS.get(client, client)}  ·  {_compact_metadata_label(client_meta)}  ·  '
            f'Skills {skill_mark}  MCP {mcp_mark}'
        )
    return labels


def catalogue_labels(catalogue, names):
    return {
        name: f'{name}  ·  {_compact_metadata_label(catalogue_metadata(catalogue, name))}'
        for name in names
    }


def resolve_scope_target(args, parser):
    scope = args.scope
    if scope is None:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            parser.error('Scope is required in non-interactive mode. Use --scope global or --scope project.')
        print('Choose installation scope:')
        print('  1. project  Write native files below the current project root')
        print('  2. global   Write native files below your home directory')
        while True:
            answer = input('Scope [project/global]: ').strip().lower()
            if answer in {'1', 'project', 'p'}:
                scope = 'project'
                break
            if answer in {'2', 'global', 'g'}:
                scope = 'global'
                break
            print('Choose project or global.')
    if scope == 'project' and args.target_home is not None:
        parser.error('--target-home is only valid with --scope global; use --project-root for project scope.')
    if scope == 'global' and args.project_root is not None:
        parser.error('--project-root is only valid with --scope project.')
    if scope == 'global':
        target = args.target_home.expanduser() if args.target_home is not None else Path.home()
        if not target.is_absolute():
            parser.error('--target-home must be an absolute path')
    else:
        target = args.project_root.expanduser() if args.project_root is not None else Path.cwd()
    target = target.resolve()
    if not target.is_dir():
        parser.error(f'Installation target must be an existing directory: {target}')
    return scope, target


def checklist(screen, clients, title='clients to configure', labels=None, groups=None, allow_empty=False, required=None, initial_selected=None, back_label=None):
    labels = LABELS if labels is None else labels
    required = set(required or [])
    curses.curs_set(0)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_MAGENTA, -1)
        curses.init_pair(2, curses.COLOR_CYAN, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
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
        compact = width < 78 or height < 24
        content_x = 2 if compact else 3

        def draw_at(row, column, text, style=0, max_width=None):
            if row < 0 or row >= height - 1 or column >= width - 1:
                return
            available = width - column - 1 if max_width is None else min(max_width, width - column - 1)
            if available > 0:
                screen.addnstr(row, column, text, available, style)

        accent = curses.color_pair(1) if curses.has_colors() else curses.A_BOLD
        secondary = curses.color_pair(2) if curses.has_colors() else curses.A_DIM
        checked = curses.color_pair(3) if curses.has_colors() else curses.A_BOLD
        warning = curses.color_pair(4) if curses.has_colors() else curses.A_BOLD
        muted = curses.A_DIM
        active_style = accent | curses.A_BOLD
        title_style = curses.A_BOLD
        selected_count = f'{len(selected)}/{len(clients)} selected'

        if compact:
            draw_at(1, content_x, 'SSS', active_style)
            draw_at(1, content_x + 6, 'WORKSTATION SETUP', secondary | curses.A_BOLD)
            draw_at(3, content_x, f'Select {title}', title_style)
            draw_at(4, content_x, 'Native Skills + MCP configuration', muted)
            list_row = 6
        else:
            for row, line in enumerate(BANNER.splitlines(), 1):
                draw_at(row, content_x, line, muted)
            draw_at(8, content_x, 'WORKSTATION SETUP', active_style)
            draw_at(8, width - len(selected_count) - 4, selected_count.upper(), secondary | curses.A_BOLD)
            draw_at(9, content_x, 'Native Skills + MCP configuration', muted)
            draw_at(11, content_x, f'Select {title}', title_style)
            draw_at(12, content_x, 'Choose what to configure. Space toggles; Enter continues.', muted)
            list_row = 14

        list_bottom = max(list_row + 1, height - 5)
        visible = max(1, list_bottom - list_row)
        display_cursor = len(rows) + 1 if cursor == back_cursor else cursor - 1 if cursor else 0
        if cursor > 0:
            offset = max(0, min(offset, display_cursor))
            if display_cursor >= offset + visible:
                offset = display_cursor - visible + 1
        end = min(len(display_rows), offset + visible)

        all_enabled = len(selected) == len(clients)
        all_active = cursor == 0
        all_style = active_style if all_active else checked if all_enabled else title_style
        all_marker = '●' if all_enabled else '○'
        all_label = f"Select all {title.split(' to ', 1)[0]}"
        draw_at(list_row, content_x, '▌' if all_active else ' ', active_style if all_active else 0)
        draw_at(list_row, content_x + 2, all_marker, checked if all_enabled else secondary)
        draw_at(list_row, content_x + 5, all_label, all_style)
        draw_at(list_row, width - len(selected_count) - 4, selected_count, secondary)

        for index in range(offset, end):
            row = display_rows[index]
            if row is None:
                continue
            name, members, is_group = row
            active = index + 1 == cursor if index < len(rows) else cursor == back_cursor
            y = list_row + 1 + index - offset
            if back_label and index == len(rows) + 1:
                draw_at(y, content_x, '▌' if active else ' ', active_style if active else 0)
                draw_at(y, content_x + 2, '↩', secondary if not active else active_style)
                draw_at(y, content_x + 5, name, active_style if active else title_style)
                continue
            count = len(selected.intersection(members))
            mark = '●' if count == len(members) else '◐' if count else '○'
            group_index = next((number for number, group in enumerate(groups or []) if group[1] is members), None)
            prefix = ('▸' if group_index in collapsed else '▾') if is_group else ' '
            raw_label = f'{name} ({count}/{len(members)})' if is_group else str(labels.get(name, name))
            if not is_group and name in required:
                metadata_separator = '  ·  Setup '
                if metadata_separator in raw_label:
                    primary, metadata = raw_label.split(metadata_separator, 1)
                    raw_label = f'{primary} · REQUIRED{metadata_separator}{metadata}'
                else:
                    raw_label += ' · REQUIRED'
            metadata_separator = '  ·  Setup '
            metadata_text = ''
            capability_text = ''
            if not is_group and metadata_separator in raw_label:
                primary, metadata = raw_label.split(metadata_separator, 1)
                metadata_text = 'Setup ' + metadata
                capability_separator = '  ·  Skills '
                if capability_separator in metadata_text:
                    metadata_text, capability = metadata_text.split(capability_separator, 1)
                    capability_text = '·  Skills ' + capability
                max_label_width = max(8, width - content_x - 9)
                metadata_width = len('·  ' + metadata_text)
                capability_width = len(capability_text) + 1 if capability_text else 0
                primary_width = max(8, max_label_width - metadata_width - capability_width)
                primary = textwrap.shorten(primary, primary_width, placeholder='…')
                label = prefix + ' ' + primary
            else:
                label = prefix + ' ' + textwrap.shorten(raw_label, max(8, width - content_x - 9), placeholder='…')
            row_style = active_style if active else checked if count else secondary if is_group else 0
            marker_style = active_style if active else checked if count else secondary
            metadata_style = accent if active else checked if count else secondary
            capability_style = metadata_style | curses.A_BOLD
            draw_at(y, content_x, '▌' if active else ' ', active_style if active else 0)
            draw_at(y, content_x + 2, mark, marker_style)
            draw_at(y, content_x + 5, label, row_style)
            if metadata_text:
                metadata_start = content_x + 5 + len(label) + 1
                metadata_available = width - metadata_start - 1
                if metadata_available > 0:
                    metadata_label = '·  ' + metadata_text
                    draw_at(y, metadata_start, metadata_label, metadata_style, metadata_available)
                    if capability_text:
                        capability_start = metadata_start + len(metadata_label) + 1
                        capability_available = width - capability_start - 1
                        if capability_available > 0:
                            draw_at(y, capability_start, capability_text, capability_style, capability_available)

        draw_at(height - 4, 2, '─' * min(width - 4, 76), muted)
        controls = '↑↓ navigate   ←→ groups   Space toggle   Enter continue   q quit' if groups else '↑↓ navigate   Space toggle   Enter continue   q quit'
        if back_label:
            controls = controls.replace('   q quit', '   b back   q quit')
        if width < 52:
            controls = '↑↓ move   Space select   Enter continue   q quit'
            if back_label:
                controls = controls.replace('   q quit', '   b back   q quit')
        draw_at(height - 3, 2, controls, muted)
        status = message or (f'Rows {offset + 1}–{end} of {len(rows)}' if len(rows) > visible else '')
        draw_at(height - 2, 2, status, warning if message else secondary)
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


def select_clients(clients, client_config, scope, initial_selected=None):
    return select_options(
        clients,
        f'clients to configure · {scope} scope',
        client_labels(client_config, scope),
        initial_selected=initial_selected,
        back_label='Back',
    )


def print_change_recap(target_root, scope, clients, skills, groups, servers, preview_only=False, plan=None, skill_catalogue=None, mcp_catalogue=None, guardrails=False):
    width = max(20, min(88, shutil.get_terminal_size((88, 24)).columns - 2))
    content_width = width - 4
    color = sys.stdout.isatty() and os.environ.get('TERM', 'dumb') != 'dumb' and 'NO_COLOR' not in os.environ
    unicode_borders = os.environ.get('TERM', 'dumb') != 'dumb'
    top, bottom, side, rule = ('┌', '└', '│', '─') if unicode_borders else ('+', '+', '|', '-')
    top_end, bottom_end = ('┐', '┘') if unicode_borders else ('+', '+')
    escape = chr(27)
    reset = f'{escape}[0m'
    style_codes = {
        'title': f'{escape}[1;36m',
        'status': f'{escape}[1;32m',
        'section': f'{escape}[1;35m',
        'subsection': f'{escape}[1m',
        'item': f'{escape}[1m',
        'meta': f'{escape}[2m',
        'warning': f'{escape}[1;33m',
    }

    def paint(text, style):
        if not color or style not in style_codes:
            return text
        return f'{style_codes[style]}{text}{reset}'

    lines = []

    def add(text='', style='normal'):
        lines.append((text, style))

    add('SSS / CHANGE RECAP', 'title')
    add('PREVIEW COMPLETE' if preview_only else 'READY TO APPLY', 'status')
    add()
    add('TARGET', 'section')
    add(f'• Scope: {scope}')
    add(f'• Root: {target_root}')

    if clients:
        add()
        add(f'CLIENTS · {len(clients)} selected', 'section')
        for client in clients:
            add(f'• {LABELS.get(client, client)}', 'item')

    if skills:
        add()
        add(f'SKILLS · {len(skills)} selected', 'section')
        for group_name, group_members in groups:
            selected = [name for name in group_members if name in skills]
            if not selected:
                continue
            add(f'  {group_name}', 'subsection')
            for name in selected:
                add(f'    • {name}', 'item')
                if skill_catalogue:
                    add(f'      {_compact_metadata_label(catalogue_metadata(skill_catalogue, name))}', 'meta')

    if servers:
        add()
        add(f'MCP · {len(servers)} selected', 'section')
        for name in servers:
            add(f'• {name}', 'item')
            if mcp_catalogue:
                add(f'  {_compact_metadata_label(catalogue_metadata(mcp_catalogue, name))}', 'meta')

    if plan and plan.warnings:
        add()
        add('CONFLICTS · skipped by default', 'section')
        for warning in plan.warnings:
            add(f'• {warning}', 'warning')

    if plan:
        changes = plan.planned_changes()
        updates = [write for write in changes if write.display_action == 'replace' or write.action == 'update']
        if updates:
            add()
            add(f'REPLACEMENTS · {len(updates)} planned with --update or --force', 'section')
            for write in updates:
                add(f'• {write.label}: {write.path}', 'item')

    if guardrails:
        add()
        add('AI GUARDRAILS · 1 selected', 'section')
        add('• AGENTS.md', 'item')
        add('  Project-level agent instructions; soft guardrail only.', 'meta')

    if not skills and not servers and not guardrails:
        add()
        add('• No Skills, MCP servers, or security changes selected.', 'warning')

    add()
    add('PREVIEW ONLY · No changes applied.' if preview_only else 'REVIEW THE SELECTIONS BEFORE APPLYING.', 'status')

    print('\n' + top + rule * (width - 2) + top_end)
    for line, style in lines:
        indent = line[:len(line) - len(line.lstrip())]
        wrapped = textwrap.wrap(
            line,
            content_width,
            subsequent_indent=indent + '  ',
            break_on_hyphens=False,
        ) or ['']
        for part in wrapped:
            text = part.ljust(content_width)
            print(f'{side} {paint(text, style)} {side}')
    print(bottom + rule * (width - 2) + bottom_end)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', action='store_true', help='Validate catalogues and public Skill packages, then exit.')
    parser.add_argument('--check', action='store_true', help='Preview only, without asking to apply.')
    parser.add_argument('--verbose', action='store_true', help='List planned file paths without showing their contents.')
    parser.add_argument('--scope', choices=['global', 'project'], help='Installation scope. Interactive runs ask when omitted.')
    parser.add_argument('--project-root', type=Path, help='Existing project directory for --scope project. Defaults to the current directory.')
    parser.add_argument('--target-home', type=Path, help='Absolute installation home for --scope global. Defaults to the current user home.')
    parser.add_argument('--update', action='store_true', help='Replace selected existing Skill packages and MCP entries after confirmation.')
    parser.add_argument('--force', action='store_true', help='Alias for --update; still previews, backs up, and asks for confirmation.')
    args = parser.parse_args()
    try:
        client_config = yaml.safe_load((ROOT / 'config/clients.yml').read_text(encoding='utf-8'))
        skill_data = yaml.safe_load((ROOT / 'catalogue/skills.yml').read_text(encoding='utf-8'))
        skill_catalogue = skill_data.get('skill_catalogue') if isinstance(skill_data, dict) else None
        mcp_catalogue = yaml.safe_load((ROOT / 'catalogue/mcp.yml').read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        parser.error(f'Cannot load project configuration: {error}')
    try:
        skill_count, mcp_count = validate_catalogues(ROOT, skill_catalogue, mcp_catalogue, client_config)
        required_skills = skill_catalogue.get('required_skills', [])
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        parser.error(str(error))
    if args.validate:
        print(f'Catalogues valid: {skill_count} Skills, {mcp_count} MCP servers, {len(client_config["client_skill_paths"])} clients.')
        return 0
    scope, target_root = resolve_scope_target(args, parser)
    print(BANNER)
    print(f'\nSSS  /  Workstation configuration  /  {scope}\n')
    required_components = ['skills'] if required_skills else []
    component_options = {
        key: label for key, label in COMPONENT_LABELS.items()
        if scope == 'project' or key != 'guardrails'
    }
    components = []
    clients = []
    skills = []
    groups = []
    selected_mcp = []
    selection_complete = False

    while not selection_complete:
        components = select_options(
            list(component_options),
            f'components to configure · {scope} scope',
            component_options,
            required=required_components,
            initial_selected=components,
        )
        if not components:
            print('Cancelled. No changes were made.')
            return 0
        if 'guardrails' in components and scope != 'project':
            parser.error('AI guardrails require --scope project so AGENTS.md stays local to the selected repository.')
        if 'skills' not in components:
            skills = []
        if 'mcp' not in components:
            selected_mcp = []

        while True:
            needs_clients = any(component in components for component in ('skills', 'mcp'))
            if needs_clients:
                client_selection = select_clients(
                    list(client_config['client_skill_paths']),
                    client_config,
                    scope,
                    initial_selected=clients,
                )
                if client_selection is BACK:
                    break
                if not client_selection:
                    print('Cancelled. No changes were made.')
                    return 0
                clients = client_selection
            else:
                clients = []

            while True:
                if 'skills' in components:
                    groups = group_skills(skill_catalogue)
                    available_skills = [name for _, members in groups for name in members]
                    skill_selection = select_options(
                        available_skills,
                        'skills to install',
                        catalogue_labels(skill_catalogue, available_skills),
                        groups,
                        allow_empty=True,
                        required=required_skills,
                        initial_selected=skills,
                        back_label='Back',
                    )
                    if skill_selection is BACK:
                        break
                    if skill_selection is None:
                        print('Cancelled. No changes were made.')
                        return 0
                    skills = skill_selection
                else:
                    skills = []
                    groups = []

                if 'mcp' in components:
                    available_mcp = list(mcp_catalogue['mcp_servers'])
                    mcp_selection = select_options(
                        available_mcp,
                        'MCP servers to configure',
                        catalogue_labels(mcp_catalogue, available_mcp),
                        allow_empty=True,
                        initial_selected=selected_mcp,
                        back_label='Back',
                    )
                    if mcp_selection is BACK:
                        if 'skills' in components:
                            continue
                        break
                    if mcp_selection is None:
                        print('Cancelled. No changes were made.')
                        return 0
                    selected_mcp = mcp_selection
                else:
                    selected_mcp = []

                selection_complete = True
                break

            if selection_complete:
                break
    try:
        validate_scope_capabilities(scope, components, clients, client_config)
        servers = resolve_mcp_servers(selected_mcp, mcp_catalogue)
        plan = build_plan(
            ROOT,
            target_root,
            components,
            clients,
            skills,
            skill_catalogue,
            servers,
            client_config,
            allow_updates=args.update or args.force,
            scope=scope,
        )
        changes = plan.planned_changes()
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        parser.error(str(error))
    print('\nInstallation targets:')
    for client in clients:
        client_meta = client_config['client_metadata'][client]
        client_caps = client_config['client_capabilities'][client]
        print(f"  {LABELS.get(client, client)} [{metadata_summary(client_meta, 'complexity')}]")
        print(
            '    Capabilities: '
            f"Skills global={'yes' if client_caps['skills']['global'] else 'no'}, project={'yes' if client_caps['skills']['project'] else 'no'}; "
            f"MCP global={'yes' if client_caps['mcp']['global'] else 'no'}, project={'yes' if client_caps['mcp']['project'] else 'no'}"
        )
        if 'skills' in components:
            print(f"    Skills: {target_root / client_config['client_skill_paths'][client]}")
        if 'mcp' in components:
            path = target_root / client_config['mcp_client_paths'][client]
            if client == 'opencode' and (path.with_suffix('.jsonc').is_file() or path.with_suffix('.jsonc').is_symlink()):
                path = path.with_suffix('.jsonc')
            print(f"    MCP: {path} ({client_config['client_capabilities'][client]['mcp_format']})")
    if 'guardrails' in components:
        print(f'  AI guardrails: {target_root / "AGENTS.md"}')
    if skills:
        print('Skills: ' + ', '.join(skills))
        for name in skills:
            print(f'  {name}: {metadata_summary(catalogue_metadata(skill_catalogue, name))}')
    for name in selected_mcp:
        definition = servers[name]
        if 'url' in definition:
            print(f'MCP {name}: remote OAuth server')
        else:
            print(f"MCP {name}: local command {definition['command']}")
        print(f'  {metadata_summary(catalogue_metadata(mcp_catalogue, name))}')
    print_change_recap(
        target_root,
        scope,
        clients,
        skills,
        groups,
        selected_mcp,
        args.check,
        plan,
        skill_catalogue,
        mcp_catalogue,
        'guardrails' in components,
    )
    print(f'\nPlanned file changes: {len(changes)}')
    if args.verbose:
        for write in changes:
            print(f'  [{write.display_action}] {write.label}: {write.path}')
    if not changes:
        print('No changes are needed. Existing conflicts were left untouched.')
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
