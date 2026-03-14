"""Quick test for Layer 4 (fuzzy) and Layer 5 (hint generator)."""
import sys
sys.path.insert(0, ".")

from core_engine.fuzzy_inference import fuzzy_infer, build_hint_context
from core_engine.hint_generator import generate_hint, generate_hint_from_gnn

# --- Layer 4: Fuzzy Inference ---

r1 = fuzzy_infer(0.9, 0.8, "low")
print(f"Test1 (low skill, high fail): {r1.hint_style} detail={r1.hint_detail}")
assert r1.hint_style == "aggressive"

r2 = fuzzy_infer(0.1, 0.9, "high")
print(f"Test2 (high skill, low fail): {r2.hint_style} detail={r2.hint_detail}")
assert r2.hint_style == "gentle"

r3 = fuzzy_infer(0.5, 0.5, "medium")
print(f"Test3 (medium all): {r3.hint_style} detail={r3.hint_detail}")
assert r3.hint_style == "moderate"

ctx = build_hint_context("Operator Error", 5, "+", "-", r1, "result = a - b")
assert ctx["hint_style"] == "aggressive"
assert ctx["bug_line"] == 5
print("Layer 4 (Fuzzy): ALL PASSED")

# --- Layer 5: Hint Generator (template mode) ---

hint = generate_hint(ctx, max_words=40)
print(f"\nHint: {hint['hint_text']}")
assert len(hint["hint_text"].split()) <= 40
assert hint["bug_type"] == "Operator Error"
print("Layer 5 (template): PASSED")

# --- End-to-end ---

full = generate_hint_from_gnn(
bug_type="Logic Error", bug_line=10,
original_token="==", buggy_token="!=",
tests_failed_ratio=0.7, model_confidence=0.6,
skill_level="low", code_snippet="if x != y:",
)
print(f"\nE2E hint: {full['hint_text']}")
print(f"Style: {full['hint_style']}, Fuzzy: {full['fuzzy']}")
assert full["hint_style"] == "aggressive"
print("End-to-end: PASSED")

print("\n=== ALL LAYER 4+5 TESTS PASSED ===")
