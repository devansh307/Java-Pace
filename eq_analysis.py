"""
EQ (Emotional Intelligence) Behavior Analysis of Call Transcripts
Analyzes Spinny AI assistant conversations for emotional intelligence dimensions.
"""

import pandas as pd
import re
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from collections import defaultdict
import warnings
import os

warnings.filterwarnings('ignore')

# ── Artifact output directory ────────────────────────────────────────────────
ARTIFACTS_DIR = "/opt/cursor/artifacts"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

CSV_PATH = "/home/ubuntu/.cursor/projects/workspace/uploads/SQL_Issues_-_9_June_edfb.csv"

# ── EQ keyword dictionaries (Hindi + English) ────────────────────────────────

EMPATHY_PHRASES = [
    r'समझ गया', r'समझ गई', r'कोई बात नहीं', r'बिल्कुल', r'जी बिल्कुल',
    r'congratulations', r'बढ़िया', r'शुभ हो', r'हाँ जी', r'जी हाँ',
    r'peace of mind', r'खुशी', r'बहुत अच्छा', r'nice',
    r'आपकी बात समझ', r'आपकी concern', r'मैं समझ',
]

APOLOGY_PHRASES = [
    r'सॉरी', r'sorry', r'माफ', r'माफ कीजिए', r'क्षमा',
    r'मुझसे गलती', r'मेरी गलती',
]

ACTIVE_LISTENING_PHRASES = [
    r'सही है ना', r'सही है\?', r'क्या मैं सही', r'मतलब',
    r'तो आप', r'आपको', r'आपका बजट', r'आपकी preference',
    r'आप कह रहे', r'यानी', r'समझा', r'ताकि मैं',
]

PATIENCE_PHRASES = [
    r'क्या आप अभी लाइन पर हैं', r'क्या आप मुझे सुन पा रहे',
    r'voice break', r'ठीक से सुन नहीं', r'फिर से बता',
    r'एक बार फिर', r'दोबारा बता', r'clear नहीं',
    r'आवाज़ थोड़ी', r'आपकी आवाज',
]

ADAPTABILITY_PHRASES = [
    r'ठीक है', r'समझ गया', r'बदलाव', r'अलग', r'दूसर',
    r'flexibility', r'छूट', r'लेकिन अगर', r'अगर आप चाहें',
    r'देख', r'option', r'ऑप्शन',
]

RAPPORT_PHRASES = [
    r'congratulations', r'बहुत बढ़िया', r'बढ़िया', r'शुभ हो',
    r'great day', r'हैव अ ग्रेट', r'आपका दिन', r'take care',
    r'future में', r'definitely connect',
]

RECOVERY_PHRASES = [
    r'सॉरी', r'sorry', r'माफ', r'लेकिन', r'however',
    r'मेरे पास', r'अभी', r'हम', r'हो सकता', r'check',
]

# Customer emotion keywords
CUSTOMER_FRUSTRATION_PHRASES = [
    r'नहीं नहीं', r'नहीं, नहीं', r'नहीं समझे', r'समझे नहीं',
    r'बार बार', r'एन, एन', r'ही चाहिए', r'प्लीज़',
    r'कॉस्टली', r'बहुत महंगा', r'इतने चार्ज',
    r'डोंट कॉल', r'don.*call',
]

CUSTOMER_SATISFACTION_PHRASES = [
    r'थैंक यू', r'thank you', r'धन्यवाद', r'बहुत अच्छा',
    r'ठीक है सर', r'अच्छा', r'ओके', r'हाँ जी', r'लेट्स गो',
    r'बिल्कुल', r'जी बिल्कुल',
]

CUSTOMER_CONFUSION_PHRASES = [
    r'हेलो\?', r'क्या\?', r'कौन', r'नहीं बताया', r'ठीक से नहीं',
    r'समझ नहीं', r'वो क्या', r'मतलब',
]


# ── Transcript parser ────────────────────────────────────────────────────────

def parse_transcript(raw: str) -> list[dict]:
    """Split raw transcript into turns."""
    turns = []
    # Remove SSML tags for cleaner text matching
    clean = re.sub(r'<[^>]+>', ' ', raw)
    parts = re.split(r'(Assistant:|User:)', clean)
    role = None
    for part in parts:
        part = part.strip()
        if part == 'Assistant:':
            role = 'Assistant'
        elif part == 'User:':
            role = 'User'
        elif part and role:
            turns.append({'role': role, 'text': part})
    return turns


def count_matches(text: str, phrases: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for p in phrases if re.search(p.lower(), text_lower))


# ── Per-call EQ scoring ──────────────────────────────────────────────────────

def score_call(row) -> dict:
    turns = parse_transcript(row['Call Transcript'])

    assistant_turns = [t['text'] for t in turns if t['role'] == 'Assistant']
    user_turns = [t['text'] for t in turns if t['role'] == 'User']

    asst_text = ' '.join(assistant_turns)
    user_text = ' '.join(user_turns)

    n_asst = max(len(assistant_turns), 1)
    n_user = max(len(user_turns), 1)

    # ── Assistant EQ dimensions ───────────────────────────────────────────
    empathy_raw = count_matches(asst_text, EMPATHY_PHRASES)
    apology_raw = count_matches(asst_text, APOLOGY_PHRASES)
    active_listening_raw = count_matches(asst_text, ACTIVE_LISTENING_PHRASES)
    patience_raw = count_matches(asst_text, PATIENCE_PHRASES)
    adaptability_raw = count_matches(asst_text, ADAPTABILITY_PHRASES)
    rapport_raw = count_matches(asst_text, RAPPORT_PHRASES)
    recovery_raw = count_matches(asst_text, RECOVERY_PHRASES)

    # Normalize per assistant turn and scale to 0-10
    def norm(raw, n=n_asst, cap=3, scale=10):
        return min((raw / n) * scale / (cap / n_asst), 10)

    # Simpler per-turn normalization capped at 10
    def score(raw, cap):
        return min(round((raw / n_asst) * 10 / cap * n_asst, 1), 10.0)

    empathy_score     = min(round(empathy_raw / n_asst * 8, 1), 10.0)
    apology_score     = min(round(apology_raw * 3, 1), 10.0)
    listening_score   = min(round(active_listening_raw / n_asst * 6, 1), 10.0)
    patience_score    = min(round(patience_raw / n_asst * 5, 1), 10.0)
    adaptability_score= min(round(adaptability_raw / n_asst * 3, 1), 10.0)
    rapport_score     = min(round(rapport_raw * 2.5, 1), 10.0)

    # ── Customer emotion ──────────────────────────────────────────────────
    frustration_raw    = count_matches(user_text, CUSTOMER_FRUSTRATION_PHRASES)
    satisfaction_raw   = count_matches(user_text, CUSTOMER_SATISFACTION_PHRASES)
    confusion_raw      = count_matches(user_text, CUSTOMER_CONFUSION_PHRASES)

    frustration_score  = min(round(frustration_raw / n_user * 10, 1), 10.0)
    satisfaction_score = min(round(satisfaction_raw / n_user * 5, 1), 10.0)
    confusion_score    = min(round(confusion_raw / n_user * 8, 1), 10.0)

    # ── Conversation quality metrics ──────────────────────────────────────
    # Call ended positively (positive closing from assistant)?
    positive_close = int(bool(re.search(r'(शुभ हो|take care|great day|हैव अ ग्रेट|धन्यवाद)', asst_text, re.I)))

    # Number of "are you on the line?" checks (patience test)
    line_checks = len(re.findall(r'लाइन पर हैं', asst_text))

    # Number of requirement adaptations (customer changed spec)
    spec_changes = len(re.findall(r'(ठीक है|समझ गया).{0,50}(लेकिन|बदल|दूसर|और|अलग)', asst_text))

    # Did assistant apologise for misunderstanding?
    misunderstanding_recovery = int(bool(re.search(r'(सॉरी|sorry|माफ).{0,80}(समझ|सुन)', asst_text, re.I)))

    # Composite EQ score (weighted average of key dimensions)
    eq_composite = round(
        empathy_score * 0.25 +
        listening_score * 0.25 +
        adaptability_score * 0.20 +
        patience_score * 0.15 +
        rapport_score * 0.10 +
        apology_score * 0.05,
        1
    )

    return {
        'buylead': row['buylead'],
        'city': row['city'],
        'capability': row['starting_capability'],
        'duration_sec': round(row['Call Duration'], 1),
        'n_assistant_turns': len(assistant_turns),
        'n_user_turns': len(user_turns),
        # Assistant EQ
        'empathy_score': empathy_score,
        'apology_score': apology_score,
        'active_listening_score': listening_score,
        'patience_score': patience_score,
        'adaptability_score': adaptability_score,
        'rapport_score': rapport_score,
        'eq_composite': eq_composite,
        # Customer emotion
        'customer_frustration': frustration_score,
        'customer_satisfaction': satisfaction_score,
        'customer_confusion': confusion_score,
        # Quality flags
        'positive_close': positive_close,
        'line_checks': line_checks,
        'spec_changes': spec_changes,
        'misunderstanding_recovery': misunderstanding_recovery,
    }


# ── Qualitative EQ observations per call ────────────────────────────────────

EQ_OBSERVATION_RULES = [
    (lambda r: r['empathy_score'] >= 5,
     "High empathy — frequent acknowledgment phrases"),
    (lambda r: r['empathy_score'] < 2,
     "Low empathy — minimal emotional acknowledgment"),
    (lambda r: r['apology_score'] > 0,
     "Apology/recovery present — good self-awareness"),
    (lambda r: r['active_listening_score'] >= 5,
     "Strong active listening — mirrors customer needs"),
    (lambda r: r['patience_score'] >= 4,
     "High patience — handles connectivity issues gracefully"),
    (lambda r: r['line_checks'] >= 4,
     "Excessive line-check repetition — may feel robotic"),
    (lambda r: r['adaptability_score'] >= 5,
     "Good adaptability — adjusts to shifting requirements"),
    (lambda r: r['customer_frustration'] >= 3,
     "Customer showed frustration — EQ test for de-escalation"),
    (lambda r: r['customer_satisfaction'] >= 4,
     "Customer expressed satisfaction — positive outcome signal"),
    (lambda r: r['misunderstanding_recovery'] == 1,
     "Recovered from misunderstanding with apology"),
    (lambda r: r['positive_close'] == 1,
     "Positive call close — rapport maintained to end"),
    (lambda r: r['n_user_turns'] > 0 and r['n_assistant_turns'] / r['n_user_turns'] > 2,
     "Assistant dominated — lower conversational balance"),
]


def get_observations(scored_row: dict) -> list[str]:
    return [msg for fn, msg in EQ_OBSERVATION_RULES if fn(scored_row)]


# ── Main analysis ─────────────────────────────────────────────────────────────

def main():
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} calls.")

    results = [score_call(row) for _, row in df.iterrows()]
    scores_df = pd.DataFrame(results)
    scores_df['observations'] = scores_df.apply(
        lambda r: '; '.join(get_observations(r.to_dict())), axis=1
    )

    # ── Save scored CSV ──────────────────────────────────────────────────
    out_csv = os.path.join(ARTIFACTS_DIR, "eq_scores.csv")
    scores_df.to_csv(out_csv, index=False)
    print(f"Scores saved → {out_csv}")

    # ── Print summary ────────────────────────────────────────────────────
    eq_dims = [
        'empathy_score', 'apology_score', 'active_listening_score',
        'patience_score', 'adaptability_score', 'rapport_score', 'eq_composite'
    ]
    print("\n=== ASSISTANT EQ DIMENSION AVERAGES (0-10 scale) ===")
    for dim in eq_dims:
        print(f"  {dim:<30} {scores_df[dim].mean():.2f}  "
              f"(min {scores_df[dim].min():.1f}, max {scores_df[dim].max():.1f})")

    print("\n=== CUSTOMER EMOTION AVERAGES ===")
    for dim in ['customer_frustration', 'customer_satisfaction', 'customer_confusion']:
        print(f"  {dim:<30} {scores_df[dim].mean():.2f}")

    print(f"\n=== COMPOSITE EQ SCORE ===")
    print(f"  Mean: {scores_df['eq_composite'].mean():.2f}  "
          f"Median: {scores_df['eq_composite'].median():.2f}  "
          f"Std: {scores_df['eq_composite'].std():.2f}")

    # ── Visualizations ───────────────────────────────────────────────────
    plt.style.use('seaborn-v0_8-whitegrid')
    colors = sns.color_palette("husl", 8)

    # 1. EQ Radar / Spider chart (average scores)
    fig = plt.figure(figsize=(8, 8))
    dim_labels = [
        'Empathy', 'Apology /\nRecovery', 'Active\nListening',
        'Patience', 'Adaptability', 'Rapport'
    ]
    raw_dims = ['empathy_score', 'apology_score', 'active_listening_score',
                'patience_score', 'adaptability_score', 'rapport_score']
    values = [scores_df[d].mean() for d in raw_dims]
    values += values[:1]  # close polygon

    angles = np.linspace(0, 2 * np.pi, len(dim_labels), endpoint=False).tolist()
    angles += angles[:1]

    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.plot(angles, values, 'o-', linewidth=2, color='#3498db')
    ax.fill(angles, values, alpha=0.25, color='#3498db')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dim_labels, size=11)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], size=8)
    ax.set_title('Assistant EQ Dimensions\n(Average across all calls)', size=13, pad=20)
    plt.tight_layout()
    radar_path = os.path.join(ARTIFACTS_DIR, "eq_radar.png")
    plt.savefig(radar_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved → {radar_path}")

    # 2. EQ composite per call (bar chart)
    fig, ax = plt.subplots(figsize=(14, 5))
    bar_colors = ['#e74c3c' if v < 3 else '#f39c12' if v < 5 else '#2ecc71'
                  for v in scores_df['eq_composite']]
    bars = ax.bar(range(len(scores_df)), scores_df['eq_composite'],
                  color=bar_colors, edgecolor='white', linewidth=0.5)
    ax.axhline(scores_df['eq_composite'].mean(), color='#2c3e50',
               linestyle='--', linewidth=1.5, label=f"Mean = {scores_df['eq_composite'].mean():.2f}")
    ax.set_xticks(range(len(scores_df)))
    ax.set_xticklabels([str(b) for b in scores_df['buylead']], rotation=45, ha='right', size=7)
    ax.set_ylabel('Composite EQ Score (0–10)', size=11)
    ax.set_title('Composite EQ Score per Call', size=13)
    ax.set_ylim(0, 10)
    ax.legend(fontsize=10)
    legend_patches = [
        mpatches.Patch(color='#e74c3c', label='Low (<3)'),
        mpatches.Patch(color='#f39c12', label='Medium (3–5)'),
        mpatches.Patch(color='#2ecc71', label='Good (≥5)'),
    ]
    ax.legend(handles=legend_patches + [
        plt.Line2D([0], [0], color='#2c3e50', linestyle='--', linewidth=1.5,
                   label=f"Mean = {scores_df['eq_composite'].mean():.2f}")
    ], fontsize=9)
    plt.tight_layout()
    bar_path = os.path.join(ARTIFACTS_DIR, "eq_per_call.png")
    plt.savefig(bar_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved → {bar_path}")

    # 3. Customer emotion vs Assistant EQ composite (scatter)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    emotions = ['customer_frustration', 'customer_satisfaction', 'customer_confusion']
    titles = ['Customer Frustration vs. EQ',
              'Customer Satisfaction vs. EQ',
              'Customer Confusion vs. EQ']
    palette = ['#e74c3c', '#2ecc71', '#f39c12']

    for ax, emo, title, color in zip(axes, emotions, titles, palette):
        ax.scatter(scores_df[emo], scores_df['eq_composite'],
                   alpha=0.7, s=70, color=color, edgecolors='white')
        # Trend line
        z = np.polyfit(scores_df[emo], scores_df['eq_composite'], 1)
        p = np.poly1d(z)
        x_line = np.linspace(scores_df[emo].min(), scores_df[emo].max(), 100)
        ax.plot(x_line, p(x_line), '--', color='#2c3e50', linewidth=1.5)
        ax.set_xlabel(emo.replace('_', ' ').title(), size=10)
        ax.set_ylabel('EQ Composite', size=10)
        ax.set_title(title, size=11)
        ax.set_ylim(0, 10)

    plt.suptitle('Customer Emotions vs. Assistant EQ Composite', size=13, y=1.02)
    plt.tight_layout()
    scatter_path = os.path.join(ARTIFACTS_DIR, "eq_emotion_scatter.png")
    plt.savefig(scatter_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved → {scatter_path}")

    # 4. EQ dimensions heatmap per call
    heat_df = scores_df[['buylead'] + raw_dims].set_index('buylead')
    heat_df.columns = ['Empathy', 'Apology', 'Active\nListening',
                       'Patience', 'Adaptability', 'Rapport']
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(heat_df.astype(float), annot=True, fmt='.1f', cmap='RdYlGn',
                vmin=0, vmax=10, linewidths=0.5, ax=ax, cbar_kws={'label': 'Score (0–10)'})
    ax.set_title('EQ Dimension Heatmap per Call (by buylead)', size=13)
    ax.set_xlabel('EQ Dimension', size=11)
    ax.set_ylabel('Buylead', size=11)
    plt.tight_layout()
    heat_path = os.path.join(ARTIFACTS_DIR, "eq_heatmap.png")
    plt.savefig(heat_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved → {heat_path}")

    # 5. EQ by city (grouped bar)
    city_eq = scores_df.groupby('city')[raw_dims].mean().round(2)
    fig, ax = plt.subplots(figsize=(12, 6))
    city_eq.plot(kind='bar', ax=ax, colormap='tab10', edgecolor='white')
    ax.set_title('Average EQ Dimensions by City', size=13)
    ax.set_ylabel('Score (0–10)', size=11)
    ax.set_xlabel('City', size=11)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right')
    ax.legend(['Empathy', 'Apology', 'Active Listening', 'Patience',
               'Adaptability', 'Rapport'], loc='upper right', fontsize=8)
    ax.set_ylim(0, 10)
    plt.tight_layout()
    city_path = os.path.join(ARTIFACTS_DIR, "eq_by_city.png")
    plt.savefig(city_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved → {city_path}")

    # 6. Distribution of composite EQ score
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(scores_df['eq_composite'], bins=10, kde=True, color='#3498db',
                 edgecolor='white', ax=ax)
    ax.axvline(scores_df['eq_composite'].mean(), color='#e74c3c', linestyle='--',
               linewidth=2, label=f"Mean = {scores_df['eq_composite'].mean():.2f}")
    ax.axvline(scores_df['eq_composite'].median(), color='#2ecc71', linestyle='-.',
               linewidth=2, label=f"Median = {scores_df['eq_composite'].median():.2f}")
    ax.set_title('Distribution of Composite EQ Score', size=13)
    ax.set_xlabel('EQ Composite Score (0–10)', size=11)
    ax.set_ylabel('Count', size=11)
    ax.legend(fontsize=10)
    plt.tight_layout()
    dist_path = os.path.join(ARTIFACTS_DIR, "eq_distribution.png")
    plt.savefig(dist_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved → {dist_path}")

    # 7. Call duration vs EQ
    fig, ax = plt.subplots(figsize=(8, 5))
    sc = ax.scatter(scores_df['duration_sec'], scores_df['eq_composite'],
                    c=scores_df['eq_composite'], cmap='RdYlGn', vmin=0, vmax=10,
                    s=80, edgecolors='#2c3e50', linewidth=0.5)
    plt.colorbar(sc, ax=ax, label='EQ Composite')
    z = np.polyfit(scores_df['duration_sec'], scores_df['eq_composite'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(scores_df['duration_sec'].min(),
                         scores_df['duration_sec'].max(), 100)
    ax.plot(x_line, p(x_line), '--', color='#2c3e50', linewidth=1.5,
            label='Trend')
    for _, r in scores_df.iterrows():
        ax.annotate(str(r['buylead'])[-5:], (r['duration_sec'], r['eq_composite']),
                    fontsize=6, alpha=0.6)
    ax.set_xlabel('Call Duration (seconds)', size=11)
    ax.set_ylabel('EQ Composite Score', size=11)
    ax.set_title('Call Duration vs. EQ Composite', size=13)
    ax.legend(fontsize=9)
    plt.tight_layout()
    dur_path = os.path.join(ARTIFACTS_DIR, "eq_duration_scatter.png")
    plt.savefig(dur_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved → {dur_path}")

    # ── Print per-call observations ──────────────────────────────────────
    print("\n=== PER-CALL KEY EQ OBSERVATIONS ===")
    print(f"{'Buylead':<12} {'City':<12} {'EQ':>5}  Observations")
    print("-" * 100)
    for _, r in scores_df.sort_values('eq_composite', ascending=False).iterrows():
        obs = r['observations'][:90] + '…' if len(r['observations']) > 90 else r['observations']
        print(f"{r['buylead']:<12} {r['city']:<12} {r['eq_composite']:>5}  {obs}")

    # ── Key insights summary ─────────────────────────────────────────────
    print("\n=== KEY EQ INSIGHTS ===")

    # Best / worst performing calls
    best = scores_df.loc[scores_df['eq_composite'].idxmax()]
    worst = scores_df.loc[scores_df['eq_composite'].idxmin()]
    print(f"  Highest EQ call : buylead {best['buylead']} ({best['city']}) – {best['eq_composite']}")
    print(f"  Lowest EQ call  : buylead {worst['buylead']} ({worst['city']}) – {worst['eq_composite']}")

    # Calls where customer was frustrated but assistant maintained EQ
    frustrated = scores_df[(scores_df['customer_frustration'] >= 2) &
                           (scores_df['eq_composite'] >= 4)]
    print(f"\n  Calls where customer showed frustration but assistant maintained good EQ: {len(frustrated)}")
    for _, r in frustrated.iterrows():
        print(f"    - buylead {r['buylead']} ({r['city']}) | EQ={r['eq_composite']} | Frustration={r['customer_frustration']}")

    # Calls where assistant had low patience despite many line checks
    robotic = scores_df[scores_df['line_checks'] >= 4]
    print(f"\n  Calls with repetitive 'are you on the line?' (≥4x) – robotic pattern risk: {len(robotic)}")
    for _, r in robotic.iterrows():
        print(f"    - buylead {r['buylead']} ({r['city']}) | line_checks={r['line_checks']}")

    # Calls with positive close
    pos_close = scores_df['positive_close'].sum()
    print(f"\n  Calls with positive closing: {pos_close}/{len(scores_df)} ({pos_close/len(scores_df)*100:.0f}%)")

    # sql vs sql_followup comparison
    print("\n  EQ by call type (capability):")
    cap_group = scores_df.groupby('capability')['eq_composite'].agg(['mean', 'count'])
    for cap, row in cap_group.iterrows():
        print(f"    {cap}: mean EQ = {row['mean']:.2f}  (n={int(row['count'])})")

    print(f"\nAll artifacts saved to {ARTIFACTS_DIR}/")
    print("Done.")

    return scores_df


if __name__ == "__main__":
    scores_df = main()
