# Load source/target pairs
src_pairs = load_pairs(src_path)
tgt_pairs = load_pairs(tgt_path)

src_map = {p.get('id') or str(i+1): p for i, p in enumerate(src_pairs)}
tgt_map = {p.get('id') or str(i+1): p for i, p in enumerate(tgt_pairs)}

combined = []
all_ids = list(dict.fromkeys(list(src_map.keys()) + list(tgt_map.keys())))
for uid in all_ids:
    combined.append({
        'id': uid,
        'source': src_map.get(uid, {}).get('source', ''),
        'target': tgt_map.get(uid, {}).get('target', '')
    })
