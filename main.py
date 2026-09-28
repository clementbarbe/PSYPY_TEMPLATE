#!/usr/bin/env python3
"""
Point d'entrée unique.

GUI :
    python main.py

CLI :
    python main.py --list-tasks

    python main.py --task stroop --design 1 --participant 01

    python main.py --task stroop --design 1 --participant 01 --windowed

    python main.py --task stroop --design 1 --participant 01 --dry-run
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# IMPORTANT : X11 doit être initialisé AVANT tkinter et PsychoPy.
#
# Sans cela, PTB/PsychHID peut afficher :
# "libX11 library was not initialized for thread-safe mode".
# ---------------------------------------------------------------------

import ctypes
import os
import sys
from pathlib import Path
import argparse


def init_x11_threads() -> None:
    """
    Initialise X11 en mode thread-safe sous Linux.

    Cette fonction doit être appelée avant l'import de tkinter,
    wxPython, Qt ou PsychoPy, car ces bibliothèques utilisent X11.
    """
    if not sys.platform.startswith("linux"):
        return

    # Workaround également reconnu par Psychtoolbox.
    os.environ.setdefault("PSYCH_XINITTHREADS", "1")

    try:
        xlib = ctypes.CDLL("libX11.so.6")
        xlib.XInitThreads()
    except Exception:
        # Une absence de libX11 ou un environnement non-X11 ne doit pas
        # empêcher le lancement du projet.
        pass


init_x11_threads()


ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Template PsychoPy pour expériences comportementales / IRMf."
    )

    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="Affiche les tâches détectées automatiquement.",
    )

    parser.add_argument("--task", help="Nom de la tâche.")
    parser.add_argument("--design", default="1", help="Identifiant du design.")
    parser.add_argument("--participant", "--pid", dest="participant")

    # Conservé pour compatibilité CLI mais non affiché dans le GUI.
    parser.add_argument("--session", default="01")

    parser.add_argument(
        "--screen",
        type=int,
        default=None,
        help="Index PsychoPy de l'écran à utiliser.",
    )

    parser.add_argument(
        "--fullscreen",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Force le plein écran ou le mode fenêtré.",
    )

    parser.add_argument(
        "--wait-trigger",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Active ou désactive explicitement l'attente du trigger. "
            "Exemples : --wait-trigger / --no-wait-trigger"
        ),
    )

    parser.add_argument(
        "--markers",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Active ou désactive les marqueurs TTL/série. "
            "Exemples : --markers / --no-markers"
        ),
    )

    parser.add_argument("--seed", type=int, default=None)

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="N'écrit pas de données sur disque.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valide tâche/design/séquence sans ouvrir de fenêtre PsychoPy.",
    )

    parser.add_argument(
        "--settings",
        default="settings.yaml",
        help="Chemin vers le fichier YAML global.",
    )

    return parser


def print_tasks() -> None:
    from tasks import list_tasks, load_task_config

    names = list_tasks()

    if not names:
        print("Aucune tâche détectée.")
        return

    print("\nTâches détectées :\n")

    for task_name in names:
        cfg = load_task_config(task_name)
        print(f"- {task_name}: {cfg.get('name', task_name)}")

        for design_id, design in cfg.get("designs", {}).items():
            print(f"    {design_id}: {design.get('name', 'Sans nom')}")

    print()


def run_cli(args: argparse.Namespace) -> int:
    from experiment import Experiment, SessionSettings
    from tasks import load_task_class, load_task_config

    if not args.task:
        raise SystemExit("--task est obligatoire en mode CLI.")

    if not args.participant:
        raise SystemExit("--participant est obligatoire en mode CLI.")

    settings = SessionSettings.from_yaml(
        path=Path(args.settings),
        participant=args.participant,
        session=args.session,
        fullscreen=args.fullscreen,
        screen_index=args.screen,
        wait_for_trigger=args.wait_trigger,
        markers_enabled=args.markers,
        save_data=not args.no_save,
    )

    task_name = args.task.lower()
    design_id = int(args.design)

    task_config = load_task_config(task_name)
    task_class = load_task_class(task_name)

    if design_id not in task_config["designs"]:
        available = ", ".join(str(x) for x in sorted(task_config["designs"]))

        raise SystemExit(
            f"Design {design_id} invalide pour '{task_name}'. "
            f"Disponibles : {available}"
        )

    if args.dry_run:
        task_class.dry_run(
            task_config=task_config,
            design_id=design_id,
            seed=args.seed,
        )

        print(
            f"[OK] Dry-run valide : "
            f"task={task_name}, design={design_id}, seed={args.seed}"
        )

        return 0

    experiment = Experiment(settings)

    try:
        saved = experiment.run(
            task_name=task_name,
            design_id=design_id,
            task_config=task_config,
            task_class=task_class,
            seed=args.seed,
        )

        if saved:
            print(f"\n[OK] Données sauvegardées : {saved}\n")

    finally:
        experiment.close()

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_tasks:
        print_tasks()
        return 0

    # Aucun --task : lancement GUI.
    if not args.task:
        from gui import show_gui

        config = show_gui(Path(args.settings))

        if config is None:
            print("Aucune expérience lancée.")
            return 0

        args.task = config["task"]
        args.design = str(config["design"])
        args.participant = config["participant"]

        # Le GUI ne montre plus la session.
        args.session = "01"

        args.screen = config["screen"]
        args.fullscreen = config["fullscreen"]
        args.wait_trigger = config["wait_trigger"]
        args.markers = config["markers_enabled"]
        args.no_save = not config["save_data"]

    return run_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())