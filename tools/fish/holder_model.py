"""Partial capture-holder predictor; abstains on lower-ranked/unsupported holders."""
# Ordered only over types with substantial pairwise discovery observations.
RANK={t:i for i,t in enumerate([7,1,2,12,3,4,8])}


def predict_leave(me, allies):
    if me['type'] not in RANK or any(c['type'] not in RANK for c in allies):
        return None
    if all(RANK[me['type']] < RANK[c['type']] for c in allies):
        return False
    return None
