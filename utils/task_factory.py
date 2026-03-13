from tasks.temporaljudgement import TemporalJudgement
from tasks.nback import NBack


def create_task(config, win):
    """
    Factory : instancie la bonne tâche à partir du dict config.
    """
    base_kwargs = {
        'win': win,
        'nom': config.get('nom'),
        'enregistrer': config.get('enregistrer'),
        'screenid': config.get('screenid'),
        'parport_actif': config.get('parport_actif'),
        'mode': config.get('mode'),
        'session': config.get('session'),
    }

    task_name = config.get('tache')

    if task_name == 'TemporalJudgement':
        return TemporalJudgement(
            **base_kwargs,
            n_trials_base=config.get('n_trials_base'),
            n_trials_block=config.get('n_trials_block'),
            n_trials_training=config.get('n_trials_training'),
            run_type=config.get('run_type'),
        )

    elif task_name == 'NBack':
        return NBack(
            **base_kwargs,
            run_type=config.get('run_type'),
            # Listes parallèles (nouvelle API)
            n_levels=config.get('n_levels', (1, 2, 3)),
            trials_per_level=config.get('trials_per_level', (15, 15, 15)),
            blocks_per_level=config.get('blocks_per_level', 3),
            # Timing
            stim_duration=config.get('stim_duration', 0.5),
            isi_duration=config.get('isi_duration', 2.0),
            target_ratio=config.get('target_ratio', 0.33),
        )

    else:
        print(f"Tâche inconnue : {task_name}")
        return None