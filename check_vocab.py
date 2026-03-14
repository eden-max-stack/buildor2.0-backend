import json
v = json.load(open('vocab.json'))
tokens = ['+', '-', '*', '/', '==', '!=', '<', '>', '<=', '>=', 'and', 'or', 'True', 'False', '0', '1']
print(f"Vocab size: {len(v)}")
for t in tokens:
    status = v.get(t, "MISSING")
    print(f"  {t!r}: {status}")

# Show first 30 entries
print("\nFirst 30 vocab entries:")
for i, (k, vid) in enumerate(sorted(v.items(), key=lambda x: x[1])):
    if i >= 30:
        break
    print(f"  [{vid}] {k!r}")
