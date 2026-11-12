# The profile scopes' ids (copied from instr.py: keep in step).
IDS = {
    0: 'world', 1: 'recv', 2: 'decide', 3: 'turn_end', 4: 'send', 5: 'queue', 7: 'approach', 8: 'wards_shop', 9: 'want_home',
    10: 'local_support', 11: 'retreat', 12: 'guard_steps', 13: 'capture_pre', 14: 'search_strikes', 16: 'hold_capture', 17: 'guard_work',
    18: 'carry_bag', 19: 'shop_guard_contest', 20: 'siege', 21: 'farm', 22: 'strike_after', 23: 'turn_order', 24: 'habit', 25: 'step_guard',
    26: 'guard_cover', 27: 'new_fight', 28: 'stand_trade', 29: 'esc_build', 30: 'esc_chase', 31: 'chase', 33: 'plan_strikes', 35: 'retreat_step',
    36: 'stand_lost_at', 37: 'drawn_home', 38: 'prey', 39: 'route', 40: 'lethal', 41: 'observe', 42: 'see_again', 43: 'refresh',
    44: 'farm_loop', 45: 'farm_picks', 46: 'channel', 47: 'heal_shield', 48: 'harm_idle', 49: 'pack_zone', 50: 'camp_trapped', 51: 'escape_walk',
    52: 'cast_enemies', 53: 'dash_away', 54: 'farm_walk', 55: 'upkeep', 56: 'chase_trade', 57: 'keep_bid', 58: 'may_reach', 59: 'stand_reach',
    60: 'safety_ctor', 61: 'threats_at', 62: 'act_tail', 63: 'other',
    64: 'rs_avoid', 65: 'rs_add', 66: 'rs_homewalk', 67: 'rs_price', 68: 'rs_move', 69: 'stand_walks', 70: 'stand_roster', 71: 'keeps_us',
    # fuel left on entry (the "fuel" field is the fuel left, not a cost)
    72: 'guard_sims',
    80: '@retreat_step', 81: '@prey', 82: '@farm', 83: '@want_home', 84: '@search', 85: '@turn_order', 86: '@retreat', 87: '@farm_loop',
    88: '@guard_exit', 89: '@guard_entry',
    79: 'last_mark', 90: '@goal', 91: '@sealed', 92: '@wants_shop', 93: '@guard_turn', 94: '@chase', 95: '@contest', 73: '@siege', 74: '@after_goal', 75: '@turn_tail', 76: '@posts',
}
