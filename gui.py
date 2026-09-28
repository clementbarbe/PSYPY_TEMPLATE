"""
GUI générique tkinter.

Aucune classe spécifique à Flanker, Stroop, N-Back ou Oddball :
les tâches et designs sont lus automatiquement dans tasks/*/config.yaml.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from experiment import sanitize_id, sanitize_session
from tasks import list_tasks, load_task_config


def show_gui(settings_path: Path) -> dict | None:
    root = tk.Tk()
    root.title("Configuration expérimentale")
    root.geometry("600x430")
    root.resizable(False, False)

    result = {"value": None}

    participant_var = tk.StringVar()
    session_var = tk.StringVar(value="01")
    screen_var = tk.IntVar(value=0)
    fullscreen_var = tk.BooleanVar(value=True)
    trigger_var = tk.BooleanVar(value=False)
    markers_var = tk.BooleanVar(value=False)
    save_var = tk.BooleanVar(value=True)

    task_names = list_tasks()

    if not task_names:
        messagebox.showerror(
            "Erreur",
            "Aucune tâche détectée dans le dossier tasks/.",
        )
        root.destroy()
        return None

    task_var = tk.StringVar(value=task_names[0])
    design_var = tk.StringVar()

    outer = ttk.Frame(root, padding=16)
    outer.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    session_frame = ttk.LabelFrame(outer, text="Session", padding=10)
    session_frame.pack(fill="x")

    ttk.Label(session_frame, text="Participant").grid(
        row=0,
        column=0,
        sticky="w",
        padx=4,
        pady=4,
    )

    ttk.Entry(
        session_frame,
        textvariable=participant_var,
        width=22,
    ).grid(row=0, column=1, sticky="w", padx=4, pady=4)

    ttk.Label(session_frame, text="Session").grid(
        row=0,
        column=2,
        sticky="w",
        padx=4,
        pady=4,
    )

    ttk.Entry(
        session_frame,
        textvariable=session_var,
        width=8,
    ).grid(row=0, column=3, sticky="w", padx=4, pady=4)

    ttk.Label(session_frame, text="Écran").grid(
        row=1,
        column=0,
        sticky="w",
        padx=4,
        pady=4,
    )

    ttk.Spinbox(
        session_frame,
        from_=0,
        to=9,
        textvariable=screen_var,
        width=6,
    ).grid(row=1, column=1, sticky="w", padx=4, pady=4)

    ttk.Checkbutton(
        session_frame,
        text="Plein écran",
        variable=fullscreen_var,
    ).grid(row=1, column=2, sticky="w", padx=4, pady=4)

    ttk.Checkbutton(
        session_frame,
        text="Attendre trigger",
        variable=trigger_var,
    ).grid(row=2, column=0, sticky="w", padx=4, pady=4)

    ttk.Checkbutton(
        session_frame,
        text="Envoyer marqueurs",
        variable=markers_var,
    ).grid(row=2, column=1, sticky="w", padx=4, pady=4)

    ttk.Checkbutton(
        session_frame,
        text="Sauvegarder",
        variable=save_var,
    ).grid(row=2, column=2, sticky="w", padx=4, pady=4)

    # ------------------------------------------------------------------
    # Tâche
    # ------------------------------------------------------------------

    task_frame = ttk.LabelFrame(outer, text="Tâche", padding=10)
    task_frame.pack(fill="x", pady=(12, 0))

    ttk.Label(task_frame, text="Tâche").grid(
        row=0,
        column=0,
        sticky="w",
        padx=4,
        pady=4,
    )

    task_box = ttk.Combobox(
        task_frame,
        textvariable=task_var,
        values=task_names,
        state="readonly",
        width=25,
    )
    task_box.grid(row=0, column=1, sticky="w", padx=4, pady=4)

    ttk.Label(task_frame, text="Design").grid(
        row=1,
        column=0,
        sticky="w",
        padx=4,
        pady=4,
    )

    design_box = ttk.Combobox(
        task_frame,
        textvariable=design_var,
        state="readonly",
        width=45,
    )
    design_box.grid(row=1, column=1, sticky="w", padx=4, pady=4)

    description = ttk.Label(
        task_frame,
        text="",
        justify="left",
        wraplength=500,
    )
    description.grid(
        row=2,
        column=0,
        columnspan=2,
        sticky="w",
        padx=4,
        pady=(10, 4),
    )

    designs_by_label: dict[str, int] = {}

    def update_designs(*_):
        nonlocal designs_by_label

        cfg = load_task_config(task_var.get())
        designs_by_label = {}

        labels = []

        for design_id, design in sorted(cfg["designs"].items()):
            label = f"{design_id} — {design.get('name', 'Sans nom')}"
            labels.append(label)
            designs_by_label[label] = design_id

        design_box["values"] = labels
        design_var.set(labels[0])

        description.configure(
            text=cfg.get("description", "")
        )

    task_box.bind("<<ComboboxSelected>>", update_designs)
    update_designs()

    # ------------------------------------------------------------------
    # Boutons
    # ------------------------------------------------------------------

    buttons = ttk.Frame(outer)
    buttons.pack(fill="x", pady=(18, 0))

    def launch():
        try:
            participant = sanitize_id(participant_var.get())
            session = sanitize_session(session_var.get())

            selected_design = designs_by_label[design_var.get()]

        except Exception as exc:
            messagebox.showerror("Configuration invalide", str(exc))
            return

        result["value"] = {
            "participant": participant,
            "session": session,
            "screen": int(screen_var.get()),
            "fullscreen": bool(fullscreen_var.get()),
            "wait_trigger": bool(trigger_var.get()),
            "markers_enabled": bool(markers_var.get()),
            "save_data": bool(save_var.get()),
            "task": task_var.get(),
            "design": selected_design,
        }

        root.destroy()

    ttk.Button(buttons, text="Annuler", command=root.destroy).pack(
        side="right",
        padx=4,
    )

    ttk.Button(buttons, text="Lancer", command=launch).pack(
        side="right",
        padx=4,
    )

    root.mainloop()
    return result["value"]