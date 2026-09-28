# PsychoPy Experiment Template

Template simple pour tâches comportementales et IRMf avec PsychoPy.

## Structure

```text
.
├── main.py                 # GUI et CLI
├── settings.yaml           # Écran, touches, trigger, TTL, audio, ET
├── experiment.py           # Session PsychoPy et cycle de vie
├── hardware.py             # Matériel optionnel
├── data.py                 # TSV, logs, dossiers participants
│
└── tasks/
    ├── base.py
    ├── flanker/
    ├── nback/
    ├── oddball/
    └── stroop/

Démarrer

bash
pip install -r requirements.txt
python main.py

CLI

Lister les tâches :

bash
python main.py --list-tasks

Lancer Stroop :

bash
python main.py \
    --task stroop \
    --design 1 \
    --participant 01 \
    --session 01

Lancer en fenêtre :

bash
python main.py \
    --task flanker \
    --design 2 \
    --participant 01 \
    --windowed

Vérifier une tâche sans ouvrir PsychoPy :

bash
python main.py \
    --task stroop \
    --design 1 \
    --participant TEST \
    --dry-run

Ajouter une tâche

Créer seulement :

text
tasks/
└── ma_tache/
    ├── task.py
    └── config.yaml

tasks/ma_tache/config.yaml

yaml
name: "Ma tâche"

designs:
  1:
    name: "Design standard"
    stim_duration: 1.0
    blocks:
      - {condition: test, n_trials: 20}

tasks/ma_tache/task.py

python
from psychopy import visual
from tasks.base import BaseTask


class Task(BaseTask):

    def setup(self):
        self.stimulus = visual.TextStim(
            self.win,
            text="",
            color="white",
            height=0.15,
        )

    def instructions(self):
        return "Instructions de la tâche."

    def build_trials(self, block):
        return [
            {"condition": block["condition"]}
            for _ in range(block["n_trials"])
        ]

    def run_trial(self, trial, block_index, trial_index, block):
        self.stimulus.text = "TEST"
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

La tâche est détectée automatiquement dans :

    le GUI ;
    python main.py --list-tasks ;
    le CLI.

Aucun registre ou import global n’est nécessaire.
Configuration globale

Modifier settings.yaml pour :

    résolution et écran ;
    fullscreen ;
    touches ;
    trigger clavier ou série ;
    TTL parallèle ou série ;
    audio PTB ;
    eye-tracker ;
    microphone ;
    chemin des données.

Données

Les sorties sont créées automatiquement :

text
data/
└── sub-01/
    └── ses-01/
        ├── stroop/
        │   ├── sub-01_ses-01_task-stroop_design-1_run-01_events_incremental.tsv
        │   ├── sub-01_ses-01_task-stroop_design-1_run-01_events.tsv
        │   └── sub-01_ses-01_task-stroop_design-1_run-01_design.json
        │
        └── logs/

Tests

bash
pytest -q

Audit spécifique Stroop :

bash
python tools/check_stroop_designs.py --repeats 200

Matériel

Le template fonctionne sans matériel spécifique.

Les fonctionnalités suivantes sont optionnelles :

    trigger clavier ;
    trigger série ;
    marqueurs parallèle ;
    marqueurs série ;
    audio PTB ;
    EyeLink ;
    microphone.

Aucune logique ne dépend de CIMA, PRISMA, TERRA ou d’un site particulier.

yaml

---

## Points à corriger avant la première exécution

Il y a deux corrections importantes à effectuer dans le code ci-dessus avant usage réel.

### Correction 1 — import Stroop dynamique

Le chargement dynamique de `tasks/stroop/task.py` implique que :

```python
from tasks.stroop.sequence import ...

doit pouvoir fonctionner.