import json
v = json.load(open('vocab.json'))

mutation_tokens = [
    "+", "-", "*", "/", "%", "**",
    "==", "!=", "<", ">", "<=", ">=",
    "and", "or", "True", "False",
]
for i in range(-2, 20):
    mutation_tokens.append(str(i))

ids = sorted([v[t] for t in mutation_tokens if t in v])
print(f"Mutation token IDs ({len(ids)}): {ids}")
print(f"Range: {min(ids)} to {max(ids)}")

# Check if contiguous
missing = [i for i in range(min(ids), max(ids)+1) if i not in ids]
print(f"Missing in range: {missing}")
