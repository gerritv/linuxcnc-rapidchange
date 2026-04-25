import rapidchange_remap
import stdglue 

from stdglue import change_epilog
from rapidchange_remap import rapidchange_change_prolog

def init(self):
    stdglue.init_stdglue(self)
    rapidchange_remap.init_rapidchange(self)