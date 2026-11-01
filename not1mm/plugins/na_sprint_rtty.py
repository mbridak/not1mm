"""North American Sprint, RTTY plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import, wildcard-import, unused-wildcard-import

# North American Sprint, RTTY
#   Same rules, exchange, scoring and QSY rule as the CW Sprint - see
#   na_sprint_cw.py for the full summary. All logic lives in that module;
#   this file only changes the contest identity and mode.
#   Dates:              Mar & Sep, 0000-0359 UTC
#   Suggested freqs:    above 3580, 7080, 14080 kHz
#   Find rules at:      https://ncjweb.com/Sprint-Rules.pdf
#   Cabrillo name:      NA-SPRINT-RTTY

from not1mm.plugins.na_sprint_cw import *  # noqa: F401,F403

name = "NA SPRINT RTTY"
cabrillo_name = "NA-SPRINT-RTTY"
mode = "RTTY"  # CW SSB BOTH RTTY
