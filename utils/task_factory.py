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
            design_id=config.get('design_id', 1),
            block_sequence=config.get('block_sequence', None),
            rest_duration=config.get('rest_duration', None),
            stim_duration=config.get('stim_duration', None),
            isi_duration=config.get('isi_duration', None),
            target_ratio=config.get('target_ratio', 0.33),
        )

    else:
        print(f"Tâche inconnue : {task_name}")
        return None