# PSYPY Template — framework fMRI PsychoPy / PyQt6

Framework compact pour développer et exécuter des tâches comportementales et fMRI avec une architecture commune, reproductible et lisible par un chercheur non spécialiste de Python.

Les quatre tâches fournies sont **Flanker**, **N-Back**, **Oddball auditif** et **Stroop**. Le style visuel historique du menu PyQt6 est conservé ; l'acquisition PsychoPy s'exécute désormais dans un **QThread** afin de ne pas bloquer l'interface.

## Architecture

```text
.
├── config/
│   └── settings.yaml       # écran, trigger, réponses, marqueurs, ET, audio
├── core/
│   ├── config.py           # SessionSettings + validation BIDS
│   ├── clock.py            # horloge expérimentale / t=0 scanner
│   ├── data.py             # events.tsv incrémental + sidecar JSON
│   ├── design.py           # DesignGenerator + export du plan
│   ├── experiment.py       # orchestration d'un run
│   ├── logging.py          # console + log fichier
│   └── errors.py
├── hardware/
│   ├── triggers.py         # trigger scanner + marqueurs parallèle/série
│   ├── response_box.py     # clavier / boîtier série
│   ├── eyetracker.py       # EyeLink / Tobii
│   ├── audio.py
│   ├── microphone.py
│   ├── screen.py
│   └── mock.py             # simulation laptop
├── gui/
│   ├── menu.py             # menu PyQt6, style d'origine
│   └── worker.py           # exécution de l'expérience dans un QThread
├── tasks/
│   ├── base.py             # cycle de vie commun
│   ├── flanker/
│   ├── nback/
│   ├── oddball/
│   └── stroop/
├── stimuli/                # stimuli partagés
├── tests/                  # tests de développement
├── main.py                 # point d'entrée unique
└── requirements.txt
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate       # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Les SDK EyeLink (`pylink`) et Tobii (`tobii_research`) sont optionnels et doivent être installés uniquement sur les postes concernés.

## Lancement

Menu graphique :

```bash
python main.py
```

Lister les tâches et les designs sans importer PsychoPy :

```bash
python main.py --list-tasks
```

Valider un Stroop sans ouvrir de fenêtre :

```bash
python main.py --task stroop --design 4 --participant TEST --dry-run --seed 42
```

Lancer un run en mode simulation hardware :

```bash
python main.py \
  --task flanker \
  --design 1 \
  --participant 01 \
  --session 01 \
  --run auto \
  --mock \
  --windowed
```

Le mode Mock simule le trigger, les marqueurs et l'eye-tracker ; les réponses participant restent saisies au clavier afin de permettre un test réaliste sur un portable.

## Générateur de design commun

`core/design.py` centralise les briques de randomisation utiles aux tâches. Pour un paradigme simple :

```python
from core.design import DesignGenerator

generator = DesignGenerator(
    conditions=["congruent", "incongruent"],
    n_blocks=4,
    trials_per_block=20,
    max_consecutive=3,
    iti=(1.5, 3.0),
    seed=42,
)

design = generator.generate()
```

Le générateur fournit également des helpers explicites pour :

- équilibrer des catégories ;
- mélanger une liste avec une limite de répétitions consécutives ;
- produire un jitter stratifié ;
- exporter un plan JSON + TSV avant l'acquisition.

Les tâches complexes peuvent conserver leur logique scientifique spécifique. Par exemple, le Stroop utilise son générateur spécialisé pour ses contraintes mot/couleur, tout en passant par le même cycle de pré-génération et de sauvegarde du framework.

## Reproductibilité et timing

Avant l'écran de trigger, **tous les trials sont générés et validés**. La graine RNG est enregistrée avec le design. Deux fichiers de plan sont écrits avant `t=0` lorsque la sauvegarde est active :

```text
sub-01_ses-01_task-stroop_run-01_design.json
sub-01_ses-01_task-stroop_run-01_planned_events.tsv
```

Le TSV planifié décrit l'ordre prévu. Il ne doit pas être confondu avec les onsets effectivement mesurés.

L'origine temporelle de l'expérience est remise à zéro à la réception du trigger scanner. Les tâches enregistrent ensuite leurs onsets à partir de cette horloge monotone PsychoPy.

## Données BIDS

Les données fonctionnelles sont écrites sous :

```text
data/
└── sub-01/
    └── ses-01/
        ├── func/
        │   ├── sub-01_ses-01_task-stroop_run-01_events.inprogress.tsv
        │   ├── sub-01_ses-01_task-stroop_run-01_events.tsv
        │   ├── sub-01_ses-01_task-stroop_run-01_events.json
        │   ├── sub-01_ses-01_task-stroop_run-01_design.json
        │   └── sub-01_ses-01_task-stroop_run-01_planned_events.tsv
        └── logs/
```

Après chaque trial, `events.inprogress.tsv` est réécrit de façon atomique et synchronisé sur disque. En cas de crash, il contient donc les essais déjà terminés. À la fin normale, `events.tsv` est finalisé atomiquement et accompagné d'un JSON sidecar.

Un numéro de run déjà existant n'est **jamais écrasé**. En mode `auto`, le premier numéro libre est choisi.

## Console opérateur

Après chaque essai, le framework produit une ligne homogène, par exemple :

```text
[Trial 12/50 | Bloc 2/4] Condition: incongruent | Onset: 10.234s | Réponse: left (Correct, RT: 420 ms)
```

Les détails restent également disponibles dans le fichier de log de session.

## Ajouter une tâche

Créer seulement :

```text
tasks/
└── ma_tache/
    ├── __init__.py
    ├── config.yaml
    └── task.py
```

Une tâche est détectée automatiquement si ces fichiers existent. Aucun registre global n'est nécessaire.

Exemple minimal :

```python
from tasks.base import BaseTask


class Task(BaseTask):
    """Tâche de démonstration."""

    def setup(self) -> None:
        """Crée les stimuli spécifiques."""
        from psychopy import visual
        self.stimulus = visual.TextStim(self.win, text="TEST", color="white")

    def instructions(self) -> str:
        """Retourne les consignes."""
        return "Appuyez sur une touche pour commencer."

    def build_trials(self, block: dict) -> list[dict]:
        """Construit le bloc avant le trigger."""
        return [{"condition": block["condition"]} for _ in range(block["n_trials"])]

    def run_trial(self, trial, block_index, trial_index, block) -> dict:
        """Présente un essai et retourne son événement."""
        self.stimulus.draw()
        self.win.flip()
        onset = self.clock.time
        return self.record(
            block_index=block_index,
            trial_index=trial_index,
            block=block,
            onset=onset,
            duration=1.0,
            trial_type=trial["condition"],
        )
```

## Hardware

Les tâches ne connaissent pas les ports physiques. Elles appellent uniquement la façade `HardwareManager` :

- `wait_for_trigger()` ;
- `marker(code)` ;
- `response_box.get_keys(...)` ;
- `eyetracker_message(...)` ;
- `audio.play_scheduled(...)`.

Les détails BNC/parallèle/série/EyeLink/Tobii restent donc confinés dans `hardware/`.

## Tests

```bash
pytest -q
```

Les tests de design, découverte, configuration et sauvegarde ne nécessitent pas de fenêtre PsychoPy. C'est volontaire : une CI ou un ordinateur de doctorant peut contrôler la logique expérimentale sans disposer du matériel du scanner.
