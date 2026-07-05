import sys
import pstats
import cProfile
from pstats import SortKey

from not1mm.__main__ import run


cProfile.run("sys.exit(run())", "stats")

p = pstats.Stats("stats")
p.strip_dirs().sort_stats(SortKey.TIME).print_stats(10)
p.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(10)
