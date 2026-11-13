"""North American Sprint, RTTY plugin

Same rules, exchange, scoring and QSY rule as the CW Sprint -- see
:mod:`not1mm.plugins.na_sprint_cw` for the full summary.  This file only
changes the contest identity and mode.

80, 40 and 20m only, 0000-0359 UTC in March and September.  Suggested
frequencies: above 3580, 7080 and 14080 kHz.

Cabrillo name: NA-SPRINT-RTTY
"""

from not1mm.plugins.na_sprint_cw import Contest as SprintContest


class Contest(SprintContest):
    """North American Sprint, RTTY."""

    DisplayName = "NA SPRINT RTTY"
    CabrilloName = "NA-SPRINT-RTTY"
    Mode = "RTTY"
