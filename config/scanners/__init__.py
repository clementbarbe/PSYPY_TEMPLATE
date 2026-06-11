"""
Scanner registry — factory function for scanner configurations.

Usage:
    from config.scanners import get_scanner, list_scanners

    scanner = get_scanner('cima')
    print(list_scanners())
"""

from __future__ import annotations

from config.scanners.base import ScannerConfig
from config.scanners.cima import CimaConfig
from config.scanners.terra import TerraConfig
from config.scanners.prisma import PrismaConfig

_REGISTRY: dict[str, ScannerConfig] = {
    'cima': CimaConfig(),
    'terra': TerraConfig(),
    'prisma': PrismaConfig(),
    'pc': ScannerConfig(name='pc'),   # bare default
}


def get_scanner(name: str) -> ScannerConfig:
    """Return scanner config by name (case-insensitive)."""
    key = name.strip().lower()
    if key not in _REGISTRY:
        available = ', '.join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"Unknown scanner '{name}'. Available: {available}"
        )
    return _REGISTRY[key]


def list_scanners() -> list[str]:
    """Return sorted list of registered scanner names."""
    return sorted(_REGISTRY.keys())


def register_scanner(name: str, config: ScannerConfig) -> None:
    """Register a custom scanner config at runtime."""
    _REGISTRY[name.strip().lower()] = config