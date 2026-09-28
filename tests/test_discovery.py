from tasks import list_tasks, load_task_class, load_task_config


def test_expected_tasks_discovered():
    tasks = set(list_tasks())

    assert {"flanker", "nback", "oddball", "stroop"} <= tasks


def test_every_task_has_config_and_class():
    for task_name in list_tasks():
        config = load_task_config(task_name)
        task_class = load_task_class(task_name)

        assert config["name"]
        assert config["designs"]
        assert task_class is not None


def test_stroop_dry_run():
    config = load_task_config("stroop")
    task_class = load_task_class("stroop")

    task_class.dry_run(
        task_config=config,
        design_id=1,
        seed=123,
    )