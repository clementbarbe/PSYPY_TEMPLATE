"""
Configuration pytest.

Ajoute explicitement la racine du projet au sys.path afin que les tests
puissent importer :

    import experiment
    from tasks import ...
    from data import ...

Cela évite de dépendre du répertoire depuis lequel pytest est lancé ou
du mode d'import configuré par des plugins externes.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))