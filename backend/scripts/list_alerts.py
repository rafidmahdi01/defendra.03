import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.firebase import get_firestore
import json

db = get_firestore()
q = db.collection('alerts').order_by('created_at', direction='DESCENDING').limit(50)
docs = list(q.stream())
print('count', len(docs))
for d in docs:
    data = d.to_dict() or {}
    print(d.id, json.dumps({
        'rule_name': data.get('rule_name'),
        'title': data.get('title'),
        'description': (data.get('description') or '')[:200],
        'device_id': data.get('device_id'),
    }, ensure_ascii=False))
