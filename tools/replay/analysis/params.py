DEFAULTS = {
    'radius': 8,
    'gap': 3,
    'max_dur': 25,
    'seen_k': 5,
    'bag_q': 0.75,
    'bag_min': 36,
    'bank_gold': 150,
    'bank_rounds': 40,
    'lead_small': 25,
    'lead_big': 100,
    'gold_gems': 0.25,
    'early': 150,
    'boot': 1000,
    'seed': 1,
}

SENSITIVITY = {
    'radius': (6, 10),
    'gap': (2, 5),
    'seen_k': (3, 10),
    'bag_q': (0.5, 0.9),
    'bank_gold': (100, 250),
    'bank_rounds': (20, 80),
    'lead_small': (10, 50),
    'lead_big': (50, 200),
}


def make(**over):
    p = dict(DEFAULTS)
    p.update(over)
    return p
