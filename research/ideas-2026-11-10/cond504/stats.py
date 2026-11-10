"""Prospective decisions for a targeted change, separate from its inactive opponent half."""
import math
BOUND = math.log(19)


def decision(gain_llr, harm_llr, off_harm_llr, gain_h0=False, harm_h1=False):
    """SPRT indifference intervals are [0,.25] and [-.25,0] percentage points."""
    gain_h0 = gain_h0 or gain_llr <= -BOUND
    harm_h1 = harm_h1 or harm_llr >= BOUND
    if off_harm_llr <= -BOUND:
        return 'OFF-TARGET HARM: review', gain_h0, harm_h1
    if harm_llr <= -BOUND:
        return ('TARGET REGRESSION REVIEW: later safety alarm' if harm_h1 else 'REJECT: target harm H0'), gain_h0, harm_h1
    if not gain_h0 and gain_llr >= BOUND:
        return 'POSITIVE SCREEN: target gain H1', gain_h0, harm_h1
    if gain_h0 and harm_h1:
        return 'SMALL/UNRESOLVED: judgement review', gain_h0, harm_h1
    return None, gain_h0, harm_h1
