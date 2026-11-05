"""Additional Fish hypotheses frozen before confirmation feature inspection."""

def cassi_stun_target(candidates):
    candidates=[c for c in candidates if c['type']!=7 and not any(
        b['type']==1 and b['timer']>0 for b in c['buffs'])]
    if not candidates:
        return None
    return min(candidates,key=lambda c:(-c['strength'],c['id']))['id']


def prism_bank_ready(me, score, allies):
    # A necessary-condition hypothesis, not a complete start-tribute policy.
    return me['gems'] + score + sum(c['gems'] for c in allies if c['channelType']==2) >= 1000
