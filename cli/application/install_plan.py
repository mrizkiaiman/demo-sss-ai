"""Build deterministic workstation installation plans.

This module is the application boundary between user selections and the
filesystem deployment layer. It deliberately has no terminal or curses
concerns, so the same request can be used by interactive and automated entry
points.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..deploy import (
    DeploymentPlan,
    build_plan as build_deployment_plan,
    resolve_mcp_servers,
    validate_catalogues as validate_catalogue_definitions,
    validate_scope_capabilities,
)


class CatalogueLoadError(ValueError):
    """Raised when the bundled SSS catalogues cannot be loaded."""


@dataclass(frozen=True)
class Catalogues:
    """Validated-input sources used to build an installation plan."""

    client_config: dict[str, Any]
    skill_catalogue: dict[str, Any] | None
    mcp_catalogue: dict[str, Any]


@dataclass(frozen=True)
class CatalogueSummary:
    """Counts reported by the catalogue validation command."""

    skill_count: int
    mcp_count: int
    client_count: int


@dataclass(frozen=True)
class InstallationRequest:
    """User-independent input for one deterministic installation plan."""

    root: Path
    target_root: Path
    scope: str
    components: tuple[str, ...]
    clients: tuple[str, ...]
    skills: tuple[str, ...]
    mcp_servers: tuple[str, ...]
    allow_updates: bool = False


@dataclass(frozen=True)
class InstallationPlan:
    """Deployment plan plus resolved MCP definitions for presentation."""

    deployment: DeploymentPlan
    servers: dict[str, dict[str, Any]]


def load_catalogues(root: Path) -> Catalogues:
    """Load bundled catalogue files without exposing YAML details to callers."""
    root = Path(root)
    try:
        client_config = yaml.safe_load((root / 'config/clients.yml').read_text(encoding='utf-8'))
        skill_data = yaml.safe_load((root / 'catalogue/skills.yml').read_text(encoding='utf-8'))
        mcp_catalogue = yaml.safe_load((root / 'catalogue/mcp.yml').read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        raise CatalogueLoadError(f'Cannot load project configuration: {error}') from error

    skill_catalogue = skill_data.get('skill_catalogue') if isinstance(skill_data, dict) else None
    return Catalogues(
        client_config=client_config,
        skill_catalogue=skill_catalogue,
        mcp_catalogue=mcp_catalogue,
    )


def validate_installation_catalogues(root: Path, catalogues: Catalogues) -> CatalogueSummary:
    """Validate all bundled inputs and return the stable summary used by CLI."""
    skill_count, mcp_count = validate_catalogue_definitions(
        Path(root),
        catalogues.skill_catalogue,
        catalogues.mcp_catalogue,
        catalogues.client_config,
    )
    return CatalogueSummary(
        skill_count=skill_count,
        mcp_count=mcp_count,
        client_count=len(catalogues.client_config['client_skill_paths']),
    )


def build_installation_plan(
    request: InstallationRequest,
    catalogues: Catalogues,
) -> InstallationPlan:
    """Turn selected components into a filesystem deployment plan."""
    if request.scope not in {'global', 'project'}:
        raise ValueError(f'Unsupported installation scope: {request.scope}')

    validate_scope_capabilities(
        request.scope,
        request.components,
        request.clients,
        catalogues.client_config,
    )
    servers = resolve_mcp_servers(list(request.mcp_servers), catalogues.mcp_catalogue)
    deployment = build_deployment_plan(
        request.root,
        request.target_root,
        list(request.components),
        list(request.clients),
        list(request.skills),
        catalogues.skill_catalogue,
        servers,
        catalogues.client_config,
        allow_updates=request.allow_updates,
        scope=request.scope,
    )
    return InstallationPlan(deployment=deployment, servers=servers)
