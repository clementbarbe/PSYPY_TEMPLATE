# tasks/qc/qc_nback.py
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import numpy as np


def qc_nback(csv_path):
    """
    Dashboard QC pour la tâche N-Back Go/No-Go.

    Panneaux :
        1. Précision par niveau N-Back
        2. Distribution des RT (Hits uniquement)
        3. Métriques SDT (d', Hit Rate, FA Rate)
        4. RT moyen par position dans le bloc (fatigue / apprentissage)
        5. Décomposition des réponses (Hit / Miss / FA / CR)
        6. Tableau récapitulatif
    """
    if not os.path.exists(csv_path):
        print(f"QC Error: Fichier non trouvé {csv_path}")
        return

    print(f"--- QC N-Back : {os.path.basename(csv_path)} ---")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"QC Error: Impossible de lire le CSV. {e}")
        return

    # Vérification colonnes minimales
    required = ['n_level', 'is_target', 'responded', 'rt',
                'is_correct', 'hit', 'miss', 'false_alarm', 'correct_rejection']
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"QC Error: Colonnes manquantes : {missing}")
        return

    # Dossier QC
    csv_dir = os.path.dirname(csv_path)
    qc_dir = os.path.join(csv_dir, 'qc')
    os.makedirs(qc_dir, exist_ok=True)

    # --- Préparation ---
    levels = sorted(df['n_level'].unique(), key=lambda x: int(x.split('-')[0]))
    n_levels_int = [int(l.split('-')[0]) for l in levels]
    palette = sns.color_palette("viridis", len(levels))
    color_map = dict(zip(levels, palette))

    df_hits = df[(df['hit'] == 1) & (df['rt'] > 0)].copy()

    # --- Figure ---
    plt.style.use('ggplot')
    fig = plt.figure(figsize=(20, 13))
    fig.suptitle(f"QC N-Back : {os.path.basename(csv_path)}", fontsize=16, fontweight='bold')

    gs = gridspec.GridSpec(2, 3, hspace=0.35, wspace=0.3)

    # =====================================================================
    # 1. PRÉCISION PAR NIVEAU
    # =====================================================================
    ax1 = fig.add_subplot(gs[0, 0])
    acc_by_level = df.groupby('n_level')['is_correct'].mean().reindex(levels) * 100
    bars = ax1.bar(levels, acc_by_level.values, color=[color_map[l] for l in levels],
                   edgecolor='black', linewidth=0.8)
    ax1.axhline(50, color='red', ls='--', alpha=0.5, label='Chance (50%)')
    ax1.set_ylim(0, 105)
    ax1.set_ylabel("Précision (%)")
    ax1.set_xlabel("Niveau")
    ax1.set_title("1. Précision par Niveau")
    ax1.legend(fontsize=8)

    # Annotations
    for bar, val in zip(bars, acc_by_level.values):
        if not np.isnan(val):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                     f"{val:.1f}%", ha='center', va='bottom', fontsize=9, fontweight='bold')

    # =====================================================================
    # 2. DISTRIBUTION DES RT (HITS)
    # =====================================================================
    ax2 = fig.add_subplot(gs[0, 1])
    if not df_hits.empty:
        for level in levels:
            sub = df_hits[df_hits['n_level'] == level]['rt']
            if not sub.empty:
                sns.kdeplot(sub, ax=ax2, color=color_map[level], label=level, fill=True, alpha=0.3)
        ax2.set_xlabel("RT (s)")
        ax2.set_ylabel("Densité")
        ax2.set_title(f"2. Distribution RT (Hits)\nMédiane globale: {df_hits['rt'].median():.3f}s")
        ax2.legend(fontsize=8)
    else:
        ax2.text(0.5, 0.5, "Aucun Hit", transform=ax2.transAxes, ha='center', fontsize=12)
        ax2.set_title("2. Distribution RT (Hits)")

    # =====================================================================
    # 3. MÉTRIQUES SDT (d', Hit Rate, FA Rate)
    # =====================================================================
    ax3 = fig.add_subplot(gs[0, 2])

    def compute_dprime(hit_rate, fa_rate):
        """Calcule d' avec correction log-linéaire."""
        hr = np.clip(hit_rate, 0.01, 0.99)
        far = np.clip(fa_rate, 0.01, 0.99)
        return float(np.round(np.subtract(
            np.vectorize(lambda p: float(np.squeeze(np.asarray(
                __import__('scipy.stats', fromlist=['norm']).stats.norm.ppf(p)
            ))))(hr),
            np.vectorize(lambda p: float(np.squeeze(np.asarray(
                __import__('scipy.stats', fromlist=['norm']).stats.norm.ppf(p)
            ))))(far)
        ), 3))

    sdt_records = []
    for level in levels:
        sub = df[df['n_level'] == level]
        targets = sub[sub['is_target'] == 1]
        nontargets = sub[sub['is_target'] == 0]

        n_targets = len(targets)
        n_nontargets = len(nontargets)
        n_hits = int(targets['hit'].sum()) if n_targets > 0 else 0
        n_fa = int(nontargets['false_alarm'].sum()) if n_nontargets > 0 else 0

        hr = n_hits / n_targets if n_targets > 0 else 0
        far = n_fa / n_nontargets if n_nontargets > 0 else 0

        try:
            dprime = compute_dprime(hr, far)
        except Exception:
            dprime = 0.0

        sdt_records.append({
            'level': level, 'hit_rate': hr, 'fa_rate': far, 'dprime': dprime
        })

    sdt_df = pd.DataFrame(sdt_records)
    x_pos = np.arange(len(levels))
    width = 0.25

    ax3.bar(x_pos - width, sdt_df['hit_rate'], width, label='Hit Rate',
            color='#2ca02c', edgecolor='black', linewidth=0.5)
    ax3.bar(x_pos, sdt_df['fa_rate'], width, label='FA Rate',
            color='#d62728', edgecolor='black', linewidth=0.5)
    ax3.bar(x_pos + width, sdt_df['dprime'] / max(sdt_df['dprime'].max(), 1), width,
            label="d' (normalisé)", color='#1f77b4', edgecolor='black', linewidth=0.5)

    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(levels)
    ax3.set_ylim(0, 1.15)
    ax3.set_ylabel("Taux / d' normalisé")
    ax3.set_title("3. Métriques SDT")
    ax3.legend(fontsize=8)

    # Annotations d'
    for i, row in sdt_df.iterrows():
        ax3.text(x_pos[i] + width, max(row['dprime'] / max(sdt_df['dprime'].max(), 1), 0) + 0.03,
                 f"d'={row['dprime']:.2f}", ha='center', fontsize=7, fontweight='bold')

    # =====================================================================
    # 4. RT PAR POSITION DANS LE BLOC
    # =====================================================================
    ax4 = fig.add_subplot(gs[1, 0])
    if not df_hits.empty and 'trial_idx' in df_hits.columns:
        for level in levels:
            sub = df_hits[df_hits['n_level'] == level]
            if not sub.empty:
                rt_by_pos = sub.groupby('trial_idx')['rt'].mean()
                ax4.plot(rt_by_pos.index, rt_by_pos.values, 'o-',
                         color=color_map[level], label=level, markersize=4, alpha=0.8)
        ax4.set_xlabel("Position dans le bloc (trial_idx)")
        ax4.set_ylabel("RT moyen (s)")
        ax4.set_title("4. RT par Position (Fatigue / Apprentissage)")
        ax4.legend(fontsize=8)
    else:
        ax4.text(0.5, 0.5, "Données insuffisantes", transform=ax4.transAxes, ha='center')
        ax4.set_title("4. RT par Position")

    # =====================================================================
    # 5. DÉCOMPOSITION DES RÉPONSES
    # =====================================================================
    ax5 = fig.add_subplot(gs[1, 1])

    resp_data = []
    for level in levels:
        sub = df[df['n_level'] == level]
        resp_data.append({
            'level': level,
            'Hit': int(sub['hit'].sum()),
            'Miss': int(sub['miss'].sum()),
            'FA': int(sub['false_alarm'].sum()),
            'CR': int(sub['correct_rejection'].sum()),
        })

    resp_df = pd.DataFrame(resp_data)
    resp_cols = ['Hit', 'Miss', 'FA', 'CR']
    resp_colors = ['#2ca02c', '#ff7f0e', '#d62728', '#1f77b4']
    bottom = np.zeros(len(levels))

    for col, color in zip(resp_cols, resp_colors):
        vals = resp_df[col].values.astype(float)
        ax5.bar(levels, vals, bottom=bottom, label=col, color=color,
                edgecolor='black', linewidth=0.5)
        bottom += vals

    ax5.set_ylabel("Nombre d'essais")
    ax5.set_xlabel("Niveau")
    ax5.set_title("5. Décomposition des Réponses")
    ax5.legend(fontsize=8)

    # =====================================================================
    # 6. TABLEAU RÉCAPITULATIF
    # =====================================================================
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')

    table_data = []
    for i, level in enumerate(levels):
        sub = df[df['n_level'] == level]
        sub_hits = df_hits[df_hits['n_level'] == level]
        n_total = len(sub)
        n_correct = int(sub['is_correct'].sum())
        acc = 100 * n_correct / n_total if n_total > 0 else 0
        mean_rt = sub_hits['rt'].mean() if not sub_hits.empty else float('nan')
        std_rt = sub_hits['rt'].std() if not sub_hits.empty else float('nan')

        table_data.append([
            level,
            f"{n_total}",
            f"{n_correct}/{n_total}",
            f"{acc:.1f}%",
            f"{mean_rt:.3f}" if not np.isnan(mean_rt) else "—",
            f"{std_rt:.3f}" if not np.isnan(std_rt) else "—",
            f"{sdt_records[i]['dprime']:.2f}",
        ])

    # Ligne totale
    total_n = len(df)
    total_correct = int(df['is_correct'].sum())
    total_acc = 100 * total_correct / total_n if total_n > 0 else 0
    total_rt = df_hits['rt'].mean() if not df_hits.empty else float('nan')
    table_data.append([
        'TOTAL',
        f"{total_n}",
        f"{total_correct}/{total_n}",
        f"{total_acc:.1f}%",
        f"{total_rt:.3f}" if not np.isnan(total_rt) else "—",
        "—",
        "—",
    ])

    col_labels = ['Niveau', 'N', 'Correct', 'Acc%', 'RT moy', 'RT std', "d'"]
    table = ax6.table(cellText=table_data, colLabels=col_labels,
                      loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.5)

    # Header styling
    for j in range(len(col_labels)):
        table[0, j].set_facecolor('#4472C4')
        table[0, j].set_text_props(color='white', fontweight='bold')

    # Total row styling
    last_row = len(table_data)
    for j in range(len(col_labels)):
        table[last_row, j].set_facecolor('#D9E2F3')
        table[last_row, j].set_text_props(fontweight='bold')

    ax6.set_title("6. Récapitulatif", pad=20)

    # --- Sauvegarde ---
    png_name = os.path.basename(csv_path).replace('.csv', '_QC.png')
    save_path = os.path.join(qc_dir, png_name)
    plt.savefig(save_path, dpi=120, bbox_inches='tight')
    plt.close()

    print(f"QC Réussi : {save_path}")
    return save_path