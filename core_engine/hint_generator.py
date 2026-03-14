"""
Layer 5: Transformer Hint Generator

Uses a local Hugging Face model (sentence-transformers/all-MiniLM-L6-v2)
to generate concise hints (max 40 words) from the structured context
produced by the fuzzy inference layer.

The approach:
  1. Build a natural-language prompt from the hint context dict.
  2. Encode it with the MiniLM sentence encoder.
  3. Select the best matching hint template via cosine similarity.
  4. Fill in the template with specific bug details.

This avoids needing a full generative LLM while still producing
context-aware, natural-sounding hints.
"""

import os
import json
from typing import Dict, Optional

# Lazy-load heavy imports
_model = None
_tokenizer = None


def _load_model():
    """Lazy-load the MiniLM model to avoid import cost at module level."""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    try:
        from transformers import AutoTokenizer, AutoModel
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModel.from_pretrained(model_name)
        _model.eval()
    except ImportError:
        _model = None
        _tokenizer = None

    return _model, _tokenizer


def _encode_text(text: str):
    """Encode text into a normalized embedding vector."""
    import torch
    model, tokenizer = _load_model()
    if model is None or tokenizer is None:
        return None

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    # Mean pooling over token embeddings
    emb = outputs.last_hidden_state.mean(dim=1)
    emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb.squeeze(0)


def _cosine_sim(a, b) -> float:
    """Cosine similarity between two tensors."""
    import torch
    return torch.dot(a, b).item()


# ---------------------------------------------------------------------------
# Hint templates organized by (hint_style, bug_type)
# Each template has a natural language pattern and a fill function.
# ---------------------------------------------------------------------------

HINT_TEMPLATES = {
    # === AGGRESSIVE (reveal almost everything) ===
    ("aggressive", "Operator Error"): [
        "Bug on line {line}: you used `{buggy}` but the correct operator is `{original}`. Replace it to fix the logic.",
        "Line {line} has an operator error. Change `{buggy}` to `{original}`.",
        "The operator `{buggy}` on line {line} should be `{original}`. This changes the computation result.",
    ],
    ("aggressive", "Logic Error"): [
        "Line {line}: the value `{buggy}` is wrong. It should be `{original}`. This is a logic error.",
        "Logic error on line {line}. You wrote `{buggy}` instead of `{original}`. Fix this comparison or value.",
        "Check line {line}. `{buggy}` should be `{original}` — this logic error changes your program's behavior.",
    ],
    ("aggressive", "None"): [
        "Your code looks correct! No bugs detected. Good job.",
        "No issues found. Your solution matches the expected approach.",
    ],

    # === MODERATE (give direction without exact answer) ===
    ("moderate", "Operator Error"): [
        "Look at the arithmetic on line {line}. The operator you chose may not produce the expected result.",
        "Line {line} has a math operation that seems off. Think about what operation is actually needed there.",
        "Recheck the operator on line {line}. Consider whether addition, subtraction, or another operation fits.",
    ],
    ("moderate", "Logic Error"): [
        "There's a logic issue on line {line}. Double-check the comparison or value used there.",
        "Line {line} contains a subtle logic mistake. Review the condition or constant carefully.",
        "Something on line {line} doesn't match the expected logic. Re-examine the value or comparison.",
    ],
    ("moderate", "None"): [
        "Your code appears correct. Consider testing edge cases to be sure.",
        "No obvious bugs detected. Run a few more test cases to confirm.",
    ],

    # === GENTLE (minimal nudge) ===
    ("gentle", "Operator Error"): [
        "Think about the math on line {line}. Is that the right operation?",
        "Revisit line {line}. Something about the arithmetic could be improved.",
        "Line {line} — does that operator do what you expect for all inputs?",
    ],
    ("gentle", "Logic Error"): [
        "Take another look at line {line}. Something small might be off.",
        "Line {line} might have a subtle issue. Trace through it with a test case.",
        "Consider whether the value on line {line} is exactly right.",
    ],
    ("gentle", "None"): [
        "Looking good! Keep testing to make sure.",
        "Your solution seems solid. Nice work.",
    ],
}


def _select_template(hint_style: str, bug_type: str, context_embedding) -> str:
    """
    Select the best template using semantic similarity between
    the context and each candidate template.
    Falls back to random selection if the model isn't available.
    """
    import random

    key = (hint_style, bug_type)
    templates = HINT_TEMPLATES.get(key)
    if not templates:
        # Fallback: try with just the style
        for k, v in HINT_TEMPLATES.items():
            if k[0] == hint_style:
                templates = v
                break
    if not templates:
        return "Review your code carefully around the flagged area."

    if context_embedding is None:
        return random.choice(templates)

    # Score each template by cosine similarity to context
    best_score = -1.0
    best_tmpl = templates[0]
    for tmpl in templates:
        tmpl_emb = _encode_text(tmpl)
        if tmpl_emb is not None:
            score = _cosine_sim(context_embedding, tmpl_emb)
            if score > best_score:
                best_score = score
                best_tmpl = tmpl

    return best_tmpl


def generate_hint(hint_context: dict, max_words: int = 40) -> dict:
    """
    Generate a natural-language hint from the structured context.

    Parameters
    ----------
    hint_context : dict
        Output of fuzzy_inference.build_hint_context(), containing:
        bug_type, bug_line, original_token, buggy_token,
        hint_style, hint_detail, code_snippet
    max_words : int
        Maximum words in the generated hint (default 40).

    Returns
    -------
    dict with keys: hint_text, hint_style, bug_type, bug_line, model_used
    """
    bug_type   = hint_context.get("bug_type", "None")
    bug_line   = hint_context.get("bug_line", -1)
    original   = hint_context.get("original_token", "?")
    buggy      = hint_context.get("buggy_token", "?")
    hint_style = hint_context.get("hint_style", "moderate")
    snippet    = hint_context.get("code_snippet", "")

    # Build context sentence for embedding
    context_sentence = (
        f"Bug type: {bug_type}. Line: {bug_line}. "
        f"Wrong token: {buggy}. Correct: {original}. "
        f"Style: {hint_style}."
    )
    if snippet:
        context_sentence += f" Code: {snippet[:200]}"

    # Encode context
    context_emb = _encode_text(context_sentence)

    # Select and fill template
    template = _select_template(hint_style, bug_type, context_emb)
    hint_text = template.format(
        line=bug_line,
        original=original,
        buggy=buggy,
    )

    # Enforce max_words limit
    words = hint_text.split()
    if len(words) > max_words:
        hint_text = " ".join(words[:max_words]) + "..."

    model_name = "sentence-transformers/all-MiniLM-L6-v2" if _model else "template-only"

    return {
        "hint_text": hint_text,
        "hint_style": hint_style,
        "bug_type": bug_type,
        "bug_line": bug_line,
        "model_used": model_name,
    }


# ---------------------------------------------------------------------------
# End-to-end convenience function
# ---------------------------------------------------------------------------

def generate_hint_from_gnn(
    bug_type: str,
    bug_line: int,
    original_token: str,
    buggy_token: str,
    tests_failed_ratio: float = 0.5,
    model_confidence: float = 0.8,
    skill_level: str = "medium",
    code_snippet: str = "",
    max_words: int = 40,
) -> dict:
    """
    Full pipeline: GNN outputs → fuzzy inference → hint generation.
    """
    from core_engine.fuzzy_inference import fuzzy_infer, build_hint_context

    fuzzy_result = fuzzy_infer(tests_failed_ratio, model_confidence, skill_level)
    context = build_hint_context(
        bug_type=bug_type,
        bug_line=bug_line,
        original_token=original_token,
        buggy_token=buggy_token,
        fuzzy=fuzzy_result,
        code_snippet=code_snippet,
    )
    hint = generate_hint(context, max_words=max_words)
    hint["fuzzy"] = {
        "hint_style": fuzzy_result.hint_style,
        "hint_detail": fuzzy_result.hint_detail,
        "rule_activations": fuzzy_result.rule_activations,
    }
    return hint
