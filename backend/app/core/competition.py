"""Shared competitive-domain constants.

MAX_SCORE — the plausibility cap for a single side's score in a match or
challenge result submission (AUD-25). Real eFootball matches are short;
even an extreme blowout stays in single/low-double digits. 30 is generous
headroom that still rejects fat-finger and abuse inputs (e.g. 999) before
they can reach a state claim or an ELO calculation. The cap is a
*validation* rule only — it does not change scoring, ELO, or standings
math, and it applies identically to tournament matches and challenges.
"""

MAX_SCORE = 30
