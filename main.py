#!/usr/bin/env python3
"""Point d'entrée unique du framework fMRI.

Sans argument, ouvre le menu PyQt6. Avec ``--task``, lance directement un run
CLI. ``--dry-run`` valide un design sans ouvrir PsychoPy.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SETTINGS = ROOT / "config" / "settings.yaml"


def init_x11_threads() -> None:
    """Active le mode thread-safe X11 avant tout import Qt/PsychoPy sous Linux."""
    if not sys.platform.startswith("linux"):
        return
    os.environ.setdefault("PSYCH_XINITTHREADS", "1")
    try:
        ctypes.CDLL("libX11.so.6").XInitThreads()
    except Exception:
        # Wayland, environnement headless ou libX11 absente : rien à faire.
        pass


init_x11_threads()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_parser() -> argparse.ArgumentParser:
    """Construit le parser CLI sans importer PsychoPy ni PyQt6."""
    parser = argparse.ArgumentParser(
        description="Framework PsychoPy/PyQt6 pour tâches comportementales et fMRI."
    )
    parser.add_argument("--list-tasks", action="store_true", help="Liste les tâches et leurs designs.")
    parser.add_argument("--task", help="Nom de la tâche à lancer.")
    parser.add_argument("--design", default="1", help="Identifiant numérique du design.")
    parser.add_argument("--participant", "--pid", dest="participant", help="Label sujet BIDS, avec ou sans sub-.")
    parser.add_argument("--session", default="01", help="Label session BIDS, avec ou sans ses-.")
    parser.add_argument("--run", default="auto", help="Numéro de run ou 'auto'.")
    parser.add_argument("--screen", type=int, default=None, help="Index PsychoPy de l'écran.")
    parser.add_argument(
        "--fullscreen",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Force ou désactive le plein écran.",
    )
    parser.add_argument("--windowed", action="store_true", help="Alias lisible de --no-fullscreen.")
    parser.add_argument(
        "--wait-trigger",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Active/désactive l'attente du trigger scanner.",
    )
    parser.add_argument(
        "--markers",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Active/désactive les marqueurs TTL/série.",
    )
    parser.add_argument(
        "--eyetracker",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Active/désactive l'eye-tracker.",
    )
    parser.add_argument("--mock", action="store_true", help="Force les périphériques scanner en mode simulation.")
    parser.add_argument("--seed", type=int, default=None, help="Graine RNG reproductible.")
    parser.add_argument("--no-save", action="store_true", help="N'écrit aucun fichier de données.")
    parser.add_argument("--dry-run", action="store_true", help="Valide le design sans ouvrir PsychoPy.")
    parser.add_argument(
        "--settings",
        type=Path,
        default=DEFAULT_SETTINGS,
        help="Chemin du settings.yaml global.",
    )
    return parser


def print_tasks() -> None:
    """Affiche les tâches auto-détectées et leurs designs disponibles."""
    from tasks import list_tasks, load_task_config

    print("\nTâches détectées :\n")
    for task_name in list_tasks():
        config = load_task_config(task_name)
        print(f"- {task_name}: {config.get('name', task_name)}")
        for design_id, design in sorted(config.get("designs", {}).items()):
            paradigm = design.get("paradigm", "block")
            print(f"    {design_id}: {design.get('name', 'Sans nom')} [{paradigm}]")
    print()


def run_cli(args: argparse.Namespace) -> int:
    """Valide les arguments puis exécute un run CLI ou un dry-run."""
    from core.config import SessionSettings
    from tasks import load_task_class, load_task_config

    if not args.task:
        raise SystemExit("--task est obligatoire en mode CLI.")
    if not args.participant:
        raise SystemExit("--participant est obligatoire en mode CLI.")

    task_name = args.task.lower()
    design_id = int(args.design)
    task_config = load_task_config(task_name)
    task_class = load_task_class(task_name)
    if design_id not in task_config["designs"]:
        available = ", ".join(str(x) for x in sorted(task_config["designs"]))
        raise SystemExit(
            f"Design {design_id} invalide pour {task_name!r}. Disponibles : {available}"
        )

    if args.dry_run:
        task_class.dry_run(task_config=task_config, design_id=design_id, seed=args.seed)
        print(f"[OK] Dry-run valide | task={task_name} | design={design_id} | seed={args.seed}")
        return 0

    from core.experiment import Experiment

    fullscreen = False if args.windowed else args.fullscreen
    settings = SessionSettings.from_yaml(
        path=args.settings,
        participant=args.participant,
        session=args.session,
        run=args.run,
        fullscreen=fullscreen,
        screen_index=args.screen,
        wait_for_trigger=args.wait_trigger,
        markers_enabled=args.markers,
        eyetracker_enabled=args.eyetracker,
        mock_mode=True if args.mock else None,
        save_data=not args.no_save,
    )
    with Experiment(settings) as experiment:
        saved = experiment.run(
            task_name=task_name,
            design_id=design_id,
            task_config=task_config,
            task_class=task_class,
            seed=args.seed,
        )
    if saved is not None:
        print(f"\n[OK] Données sauvegardées : {saved}\n")
    return 0


def main() -> int:
    """Route vers la liste des tâches, le CLI ou le menu PyQt6."""
    args = build_parser().parse_args()
    if args.list_tasks:
        print_tasks()
        return 0
    if args.task:
        return run_cli(args)

    from gui import show_gui

    return show_gui(args.settings)


if __name__ == "__main__":
    raise SystemExit(main())
