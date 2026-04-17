"""
Layer 4: Fuzzy Inference Engine

Mimics abstract human reasoning to decide hint aggressiveness.
Inputs:
  - tests_failed_ratio : float [0, 1]  (fraction of test cases failed)
  - model_confidence   : float [0, 1]  (GNN classifier softmax max)
  - skill_level        : str           ("low" | "medium" | "high")
  - question_difficulty: str           ("Easy" | "Medium" | "Hard")
  - hints_used         : int           (Number of hints previously requested)

Output:
  - hint_style : str   ("aggressive" | "moderate" | "gentle")
  - hint_detail: float [0, 1]  (how much detail to include)
  - fuzzy_scores: dict  (raw membership + rule activations for transparency)
"""

from dataclasses import dataclass
from typing import Dict


# ---------------------------------------------------------------------------
# Membership functions  (triangular / trapezoidal)
# ---------------------------------------------------------------------------

def _trap(x: float, a: float, b: float, c: float, d: float) -> float:
    """Trapezoidal membership: rises a→b, flat b→c, falls c→d."""
    if x <= a or x >= d:
        return 0.0
    if a < x < b:
        return (x - a) / (b - a)
    if b <= x <= c:
        return 1.0
    return (d - x) / (d - c)

def _tri(x: float, a: float, b: float, c: float) -> float:
    """Triangular membership (special case of trapezoidal with b==c)."""
    return _trap(x, a, b, b, c)


# --- Tests-failed membership ---
def tests_low(x: float) -> float: return _trap(x, -0.1, 0.0, 0.2, 0.4)
def tests_med(x: float) -> float: return _tri(x, 0.2, 0.5, 0.8)
def tests_high(x: float) -> float: return _trap(x, 0.6, 0.8, 1.0, 1.1)

# --- Model-confidence membership ---
def conf_low(x: float) -> float: return _trap(x, -0.1, 0.0, 0.3, 0.5)
def conf_med(x: float) -> float: return _tri(x, 0.3, 0.5, 0.7)
def conf_high(x: float) -> float: return _trap(x, 0.5, 0.7, 1.0, 1.1)

# --- Hints-used membership ---
def hints_few(x: float) -> float: return _trap(x, -0.1, 0.0, 0.8, 1.5)
def hints_some(x: float) -> float: return _tri(x, 0.5, 1.5, 2.5)
def hints_many(x: float) -> float: return _trap(x, 1.5, 2.5, 10.0, 11.0)


# ---------------------------------------------------------------------------
# Challenge Gap Calculation (Crisp Pre-Processing)
# ---------------------------------------------------------------------------
SKILL_WEIGHTS = {"low": 1, "medium": 2, "high": 3}
DIFF_WEIGHTS = {"Easy": 1, "Medium": 2, "Hard": 3}

def get_challenge_gap(skill: str, difficulty: str) -> str:
    """Reduces 2 dimensions into 1 by measuring the student's capability vs the problem."""
    gap = DIFF_WEIGHTS.get(difficulty, 2) - SKILL_WEIGHTS.get(skill, 2)
    if gap > 0: return "under_leveled"  # e.g., Low skill attempting Hard
    if gap < 0: return "over_leveled"   # e.g., High skill attempting Easy
    return "on_level"                   # e.g., Medium skill attempting Medium

# ---------------------------------------------------------------------------
# Rule base  (Mamdani-style, min-activation with Wildcards)
# ---------------------------------------------------------------------------
# Format: (tests_level, conf_level, challenge_gap, hints_level) → hint_style
# "*" acts as a wildcard (membership = 1.0 for that dimension)

RULES = [
    # --- CEILING RULE (Overrides everything) ---
    # If they have used many hints, NEVER give them the answer. Force gentle.
    ("*", "*", "*", "many", "gentle"),

    # --- UNDER-LEVELED (They are struggling with a hard problem) ---
    ("high", "high", "under_leveled", "few", "aggressive"),
    ("high", "low",  "under_leveled", "few", "moderate"),
    ("med",  "*",    "under_leveled", "few", "moderate"),
    ("*",    "*",    "under_leveled", "some", "moderate"),

    # --- ON-LEVEL (Matched difficulty) ---
    ("high", "high", "on_level", "few", "aggressive"),
    ("high", "low",  "on_level", "few", "moderate"),
    ("med",  "*",    "on_level", "few", "moderate"),
    ("low",  "*",    "on_level", "few", "gentle"),
    ("*",    "*",    "on_level", "some", "gentle"),

    # --- OVER-LEVELED (They should know this) ---
    ("high", "*", "over_leveled", "few", "moderate"),
    ("med",  "*", "over_leveled", "few", "gentle"),
    ("low",  "*", "over_leveled", "*",   "gentle"),
    ("*",    "*", "over_leveled", "some", "gentle"),
]

STYLE_DETAIL = {
    "aggressive": 0.9,
    "moderate":   0.5,
    "gentle":     0.2,
}

TESTS_FNS  = {"low": tests_low, "med": tests_med, "high": tests_high}
CONF_FNS   = {"low": conf_low,  "med": conf_med,  "high": conf_high}
HINTS_FNS  = {"few": hints_few, "some": hints_some, "many": hints_many}


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

@dataclass
class FuzzyResult:
    hint_style: str
    hint_detail: float
    rule_activations: Dict[str, float]
    winning_rule_strength: float


def fuzzy_infer(
    tests_failed_ratio: float,
    model_confidence: float,
    skill_level: str,
    question_difficulty: str,
    hints_used: int
) -> FuzzyResult:
    """
    Run Mamdani fuzzy inference and return the recommended hint style.
    """
    challenge_gap = get_challenge_gap(skill_level, question_difficulty)
    agg: Dict[str, float] = {"aggressive": 0.0, "moderate": 0.0, "gentle": 0.0}

    for t_lbl, c_lbl, g_lbl, h_lbl, out_style in RULES:
        # Calculate memberships, treating "*" as 1.0
        mu_t = TESTS_FNS[t_lbl](tests_failed_ratio) if t_lbl != "*" else 1.0
        mu_c = CONF_FNS[c_lbl](model_confidence) if c_lbl != "*" else 1.0
        mu_h = HINTS_FNS[h_lbl](hints_used) if h_lbl != "*" else 1.0
        
        # Crisp check for the gap
        mu_g = 1.0 if (g_lbl == "*" or g_lbl == challenge_gap) else 0.0

        # AND = min
        activation = min(mu_t, mu_c, mu_g, mu_h) 
        
        # OR = max (aggregate per style)
        agg[out_style] = max(agg[out_style], activation) 

    # Pick winner (highest aggregated membership)
    winner = max(agg, key=lambda k: agg[k])

    # Defuzzify detail level via weighted average
    total = sum(agg.values()) or 1e-9
    detail = sum(STYLE_DETAIL[s] * v for s, v in agg.items()) / total

    return FuzzyResult(
        hint_style=winner,
        hint_detail=round(detail, 3),
        rule_activations=agg,
        winning_rule_strength=round(agg[winner], 3),
    )

def build_hint_context(
    bug_type: str,
    bug_line: int,
    original_token: str,
    buggy_token: str,
    fuzzy: FuzzyResult,
    code_snippet: str = "",
) -> dict:
    return {
        "bug_type": bug_type,
        "bug_line": bug_line,
        "original_token": original_token,
        "buggy_token": buggy_token,
        "hint_style": fuzzy.hint_style,
        "hint_detail": fuzzy.hint_detail,
        "code_snippet": code_snippet,
    }