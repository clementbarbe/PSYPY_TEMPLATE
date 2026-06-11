"""Input validation utilities."""

from __future__ import annotations


def validate_participant_id(pid: str) -> str:
    """Sanitise participant ID: strip whitespace, check non-empty."""
    pid = pid.strip()
    if not pid:
        raise ValueError("Participant ID cannot be empty.")
    # Remove potentially problematic characters
    safe = ''.join(c for c in pid if c.isalnum() or c in '-_')
    if not safe:
        raise ValueError(f"Participant ID '{pid}' contains no valid characters.")
    return safe


def validate_session(session: str) -> str:
    """Ensure session is a zero-padded number string."""
    session = session.strip()
    if not session:
        return '01'
    try:
        return f"{int(session):02d}"
    except ValueError:
        return session


def validate_design_id(design_id: int, available: list[int]) -> int:
    """Check design_id is in the available list."""
    if design_id not in available:
        raise ValueError(
            f"Design {design_id} not available. Choose from: {available}"
        )
    return design_id