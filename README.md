# fMRI Experiment Framework

A modular PsychoPy framework for cognitive neuroimaging experiments.
Built for multi-scanner fMRI research with precise timing, hardware abstraction, and easy task creation.

---

## Features at a Glance

| Feature | Description |
|---|---|
| **Multi-scanner** | CIMA, TERRA, PRISMA configs built-in. Add your own in one file. |
| **Plug & play tasks** | Add a task = 1 Python file + 1 YAML file + 1 line in `__init__` |
| **Hardware abstraction** | Parallel port, serial, eye-tracker — tasks never touch devices directly |
| **Precise audio** | PTB-scheduled playback with preloading (sub-ms jitter) |
| **Escape = clean exit** | Press Escape anytime → data saved, eye-tracker closed, hardware reset |
| **Crash-safe data** | Every trial written to CSV immediately |
| **BIDS-inspired output** | `sub-XX/ses-XX/task/` directory structure |
| **GUI launcher** | Sober PyQt6 menu — click a design button, experiment starts |
| **Arrow keys default** | PC mode uses ← → out of the box |

---

## Quick Start

### GUI (recommended)

```bash
python main.py
```
    Fill in participant name, session, screen
    Go to the task tab (Flanker, N-Back...)
    Click Design 1 (or 2, 3, 4) → experiment starts

Command line

```bash
# PC mode
python run_experiment.py --pid 01 --task flanker --design 1

# fMRI mode on CIMA scanner
python run_experiment.py --pid 01 --task nback --design 3 --mode fmri --screen 1
```


## Project Structure

```csharp
project_root/
├── main.py                      # GUI entry point
├── run_experiment.py            # CLI entry point
│
├── config/
│   ├── constants.py             # All constants (timing, TTL, paths)
│   ├── settings.py              # ExperimentSettings dataclass
│   ├── visual_params.py         # Degrees ↔ pixels conversion
│   ├── scanners/                # One file per scanner site
│   │   ├── base.py              # ScannerConfig dataclass
│   │   ├── cima.py
│   │   ├── terra.py
│   │   └── prisma.py
│   └── tasks_config/            # One YAML per task
│       ├── flanker.yaml
│       └── nback.yaml
│
├── core/
│   ├── experiment.py            # Creates window, clock, hardware
│   ├── clock.py                 # t=0 at trigger, all timestamps relative
│   ├── events.py                # Pub/sub event bus
│   └── exceptions.py            # AbortExperiment, etc.
│
├── tasks/
│   ├── base.py                  # BaseTask ABC (template method)
│   ├── registry.py              # Lazy task registration
│   ├── flanker.py               # Eriksen Flanker
│   ├── nback.py                 # N-Back
│   └── utils/
│       ├── sequence.py          # Desequencing, jittered ISIs
│       └── sdt.py               # Signal Detection Theory
│
├── hardware/
│   ├── manager.py               # HardwareManager facade
│   ├── audio.py                 # AudioManager (PTB scheduling)
│   ├── parallel_port.py
│   ├── serial_trigger.py
│   ├── keyboard_trigger.py
│   └── eyetracker.py           # EyeLink + force reset
│
├── dataio/
│   ├── logger.py                # Console + file logger
│   ├── data_writer.py           # Incremental CSV writer
│   └── subject_handler.py       # BIDS directory creation
│
├── gui/
│   ├── launcher.py              # PyQt6 menu
│   ├── task_panels.py           # Per-task config panels
│   └── styles.py                # Stylesheet
│
├── utils/
│   ├── console.py               # Windows ANSI + safe symbols
│   ├── timing.py
│   ├── visual.py
│   └── validators.py
│
└── stimuli/
    ├── images/
    └── sounds/
```

## How To: Add a New Task (3 steps)
Step 1 — Create the task file

```python
# tasks/stroop.py
from tasks.base import BaseTask
from tasks.registry import register_task

@register_task('stroop')
class StroopTask(BaseTask):
    TASK_NAME = 'stroop'

    def _setup_stimuli(self):
        # Create your PsychoPy stimuli here
        ...

    def _get_instruction_text(self):
        return "Press LEFT for red, RIGHT for blue..."

    def _get_block_instruction(self, block_idx, block_def):
        return f"Block {block_idx + 1}" 

    def generate_trials(self, block_def):
        # Return list of trial data
        return [...]

    def run_trial(self, trial_data, block_idx, trial_idx, block_def, **kw):
        # Frame-accurate trial loop
        # Use self.get_keys() — escape is checked automatically
        # Use self.clock.time for timestamps
        # Return a record dict
        record = self._base_record(block_idx, trial_idx, block_def)
        record.update({...})
        return record
```
Step 2 — Register it (one line)

```python
# tasks/__init__.py
register_lazy('stroop', 'tasks.stroop', 'StroopTask')

Step 3 — Create the config

yaml
# config/tasks_config/stroop.yaml
task_name: stroop
designs:
  1:
    name: "Classic Stroop"
    stim_duration: 1.5
    isi_min: 1.0
    isi_max: 1.0
    rest_duration: 12.0
    instruction_duration: 3.0
    pre_block_fixation: 1.0
    blocks:
      - condition: congruent
        n_trials: 20
      - condition: incongruent
        n_trials: 20
```
Done. The task appears in the GUI automatically.
Optional — Custom GUI panel

```python
# gui/task_panels.py
@register_panel('Stroop')
class StroopPanel(QWidget):
    TASK_NAME = 'stroop'
    # Add design buttons, training options, etc.
```
How To: Remove a Task

Comment out one line:

```python
# tasks/__init__.py
# register_lazy('stroop', 'tasks.stroop', 'StroopTask')
```

Gone from GUI and CLI instantly.
How To: Add a Scanner

```python
# config/scanners/my_scanner.py
from config.scanners.base import ScannerConfig, TriggerInput, TriggerOutput

def MyScannerConfig():
    return ScannerConfig(
        name='my_scanner',
        screen_width_px=1920,
        screen_height_px=1080,
        screen_width_cm=60.0,
        viewing_distance_cm=150.0,
        trigger_input=TriggerInput.KEYBOARD,
        trigger_key='5',
        trigger_output=TriggerOutput.PARALLEL,
        parallel_port_address=0x0378,
        response_keys={'left': '1', 'right': '4', 'go': '1'},
    )
```

```python
# config/scanners/__init__.py — add one line:
from config.scanners.my_scanner import MyScannerConfig
_REGISTRY['my_scanner'] = MyScannerConfig()
```

## Useful Functions Reference

### In any task (via self.)

| Function	| What it does |
|---|---|
 | self.get_keys(key_list=['left','right'])	| Get responses. Escape auto-checked. | 
 | self.flush_keyboard()	| Clear keyboard buffer before a trial | 
 | self.show_fixation(duration)	| Fixation cross, frame-accurate, escape-aware | 
 | self.show_text_and_wait(text)	| Show text, wait for any key | 
 | self.show_timed_text(text, duration)	| Show text for N seconds | 
 | self.clock.time	| Current time since trigger (t=0) | 
 | self._base_record(block_idx, trial_idx, block_def)	| Pre-filled record with common fields| 
 | self.hardware.send_trigger(code)	| Send TTL marker | 
 | self.hardware.send_eyetracker_message(msg)	| Timestamped ET message | 

### Audio (via self.audio)

| Function	| What it does | 
|---|---|
 | self.audio.preload('name', 'path/file.wav')	|  Load file into memory (zero latency later) | 
 | self.audio.preload_tone('beep', freq=1000, duration=0.2) | 	Generate and preload a pure tone | 
 | self.audio.play_now('name') | 	Play immediately (less precise) | 
 | self.audio.play_scheduled('name', target_time, self.clock) | 	PTB-scheduled playback — call ~100ms before target | 
 | self.audio.stop('name')	 | Stop a playing sound | 
 | self.audio.stop_all()	 | Stop everything | 

### Sequence generation (import from tasks.utils)

 | Function | 	What it does | 
 |---|---|
 | desequence(trials, key_func, max_consecutive=4)	 | Shuffle with no long runs of same condition | 
 | generate_jittered_isis(n, isi_min, isi_max) | 	Uniform random ISI list | 
 | classify_sdt(is_target, responded)	 | → {hit, miss, false_alarm, correct_rejection, is_correct}


## Timing Reference

    t=0 is defined when the scanner trigger key is received
    ALL timestamps in CSV files are relative to this t=0
    Works identically in fmri and pc modes
    RT is computed as self.clock.time - stim_onset (not key.rt)
    Audio scheduling uses PTB absolute clock for sub-ms precision



## Data Output

```lua
data/
└── sub-01/
    └── ses-01/
        ├── flanker/
        │   ├── sub-01_ses-01_task-flanker_run-01_events.csv
        │   └── sub-01_ses-01_task-flanker_run-01_events_final.csv
        ├── nback/
        │   └── ...
        └── logs/
            └── sub-01_ses-01_20250101_120000.log

    _events.csv — written trial-by-trial (crash-safe)
    _events_final.csv — clean copy at end of session
```

## Emergency Exit
    Action	What happens
    Press Escape	Clean abort → data saved → ET data transferred → hardware closed
    CTRL+C	Signal handler → emergency shutdown → same cleanup
    Crash	atexit handler → best-effort cleanup

Data is saved in all cases except power loss.

## Requirements

``` shell
psychopy>=2023.1.0
PyQt6>=6.5.0
PyYAML>=6.0
numpy>=1.21
pyserial>=3.5
```