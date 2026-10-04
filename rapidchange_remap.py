from posixpath import devnull
import subprocess
from json import tool
import os
import linuxcnc
from interpreter import *
throw_exceptions = 1

def init_rapidchange(self):
    self.rapidchange = RapidChangeConfig()

class RapidChangeConfig:
    def __init__(self):
        # Read RapidChange values from ini file once at startup
        self.inifile = linuxcnc.ini(os.environ['INI_FILE_NAME'])


        self.FORCE_ALL_MANUAL_CHANGES = self.read_ini_value_bool("FORCE_ALL_MANUAL_CHANGES")
        # TODO Remove self.PROBE_AFTER_MANUAL_LOAD = self.read_ini_value_bool("PROBE_AFTER_MANUAL_LOAD")

        self.POCKET_BASE_X = self.read_ini_value("POCKET_BASE_X")
        self.POCKET_BASE_Y = self.read_ini_value("POCKET_BASE_Y")
        self.POCKET_OFFSET_X = self.read_ini_value("POCKET_OFFSET_X")
        self.POCKET_OFFSET_Y = self.read_ini_value("POCKET_OFFSET_Y")
        self.NUM_POCKETS = self.read_ini_value("NUM_POCKETS")

        #Load the rack mapping
        self.RACK_TABLE = self.read_ini_string("RACK_TABLE")
        self.rack_map = self.load_rack_map()

    def read_ini_value(self, key):
        val = self.inifile.find("RAPIDCHANGEATC", key)
        if val is None:
            raise ValueError("Couldn't find RAPIDCHANGEATC.%s", key)
        return float(val)

    def read_ini_value_bool(self, key):
        val = self.read_ini_value(key)

        if val == 0:
            return False
        elif val == 1:
            return True
        else:
            raise ValueError("Value for key %s must be 0 or 1.", key)
    

    def read_ini_string(self, key):
        val = self.inifile.find("RAPIDCHANGEATC", key)
        if val is None:
            raise ValueError("Couldn't find RAPIDCHANGEATC.%s" % key)
        return val.strip()


    def load_rack_map(self):
        """Load rackchange.tbl; returns dict tool->pocket."""
        rack_map = {}

        if not os.path.exists(self.RACK_TABLE):
            raise ValueError(
                "RapidChange rack table not found: %s" % self.RACK_TABLE
            )

        with open(self.RACK_TABLE) as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith(";") or line.startswith("#"):
                    continue

                parts = line.split(",")
                if len(parts) != 2:
                    continue

                try:
                    pocket = int(parts[0])
                    tool = int(parts[1])
                except ValueError:
                    continue

                if pocket < 1 or pocket > self.NUM_POCKETS:
                    continue

                if tool > 0:
                    rack_map[tool] = pocket

        return rack_map

def find_rack_pocket(self, tool):
    """Return RapidChange pocket for tool, or 0 if not in rack."""
    if tool <= 0:
        return 0
    return self.rapidchange.rack_map.get(tool, 0)

# Calculate X/Y position of given pocket
def get_pocket_xy(self, pocket):
    x = self.rapidchange.POCKET_BASE_X + self.rapidchange.POCKET_OFFSET_X * (pocket - 1)
    y = self.rapidchange.POCKET_BASE_Y + self.rapidchange.POCKET_OFFSET_Y * (pocket - 1)

    return (x, y)

# REMAP=M6  modalgroup=6 prolog=rapidchange_change_prolog ngc=rapidchange_m6 epilog=change_epilog
#
# Parameters required for default epilog:
#    #<tool_in_spindle>     Tx value of current tool
#    #<selected_tool>       Tx value of selected tool
#    #<current_pocket>      Index in tool table of current tool
#    #<selected_pocket>     Index in tool table of selected tool
#
# parameters required for remap ngc
#   #<rc_current_pocket>    RapidChange pocket of the current tool
#   #<rc_selected_pocket>   RapidChange pocket of the selected tool (most recent Tx)
#   
#
#   #<rc_do_rc_drop>        1 if current tool should be dropped in RapidChange pocket
#   #<rc_do_manual_drop>    1 if current tool should be dropped manually
#   #<rc_drop_x>            X location of RapidChange pocket to drop at
#   #<rc_drop_y>            Y location of RapidChange pocket to drop at
#
#   #<rc_do_rc_pickup>      1 if current tool should be picked up from RapidChange pocket
#   #<rc_do_manual_pickup>  1 if current tool should be picked up manually
#   #<rc_pickup_x>          X location of RapidChange pocket to drop at
#   #<rc_pickup_y>          Y location of RapidChange pocket to drop at
# 
#   #<rc_do_any_action>     1 if doing any drop or probe. Used to supress move to safe Z when there's nothing to do.

def rapidchange_change_prolog(self, **words):
    try:
        # trick to get RapidChange init'd without modifying PP's toplevel and remap.py modules. This is a bit of a hack, but it works.
        if not hasattr(self, "rapidchange"):
            init_rapidchange(self)

        # reload the mapping file everytime, just in case it has changed since the last time we used it
        self.rapidchange.rack_map = self.rapidchange.load_rack_map()

        if self.selected_pocket < 0:
            self.set_errormsg("M6: No tool prepared")
            return INTERP_ERROR
        
        if self.cutter_comp_side:
            # TODO disable it here instead of just erroring out.
            self.set_errormsg("M6: Cutter radius compensation must be off")
            return INTERP_ERROR

        # I really want to check for spindle_turning, but looks like there's a bug in LinuxCNC so you can't access that from Python

        # if self.spindle_turning != CANON_DIRECTION.CANON_STOPPED:
        #     self.set_errormsg("M6: Spindle must be stopped")
        #     return INTERP_ERROR
        
        # Required for default epilog
        self.params["tool_in_spindle"] = self.current_tool
        self.params["selected_tool"] = self.selected_tool
        self.params["current_pocket"] = self.current_pocket
        self.params["selected_pocket"] = self.selected_pocket

        # Get Px values from tool table for current and selected tools
        # Get RapidChange pockets from rack map
        rc_current_pocket = find_rack_pocket(self, self.current_tool)
        rc_selected_pocket = find_rack_pocket(self, self.selected_tool)

        self.params["rc_current_pocket"] = rc_current_pocket
        self.params["rc_selected_pocket"] = rc_selected_pocket
        if (rc_current_pocket == 0 and self.current_tool > 0):
            self.set_errormsg("Current tool, %i, not found in table" % self.current_tool)
            # TODO Change to try to drop current_tool into an empty pocket, if one exists. If not, then ask for manual remove
            return INTERP_ERROR
        
       
        if (rc_selected_pocket == 0 and self.selected_tool > 0):
            self.set_errormsg("Selected tool, %i, not found in table" % self.selected_tool)
            # TODO Allow user to add to table, then continue if added, else error out
            return INTERP_ERROR
        
        self.params["rc_current_pocket"] = rc_current_pocket
        self.params["rc_selected_pocket"] = rc_selected_pocket

        current_tool_in_rc = \
            rc_current_pocket > 0 \
            and rc_current_pocket <= self.rapidchange.NUM_POCKETS \
            and not self.rapidchange.FORCE_ALL_MANUAL_CHANGES
        
        do_rc_drop = \
            self.current_tool > 0 \
            and current_tool_in_rc \
            and self.current_tool != self.selected_tool
        
        do_manual_drop = \
            self.current_tool > 0 \
            and not current_tool_in_rc \
            and self.current_tool != self.selected_tool
        

        self.params["rc_do_manual_drop"] = 1 if do_manual_drop else 0
        self.params["rc_do_rc_drop"] = 1 if do_rc_drop else 0

        if do_rc_drop:
            drop_x, drop_y = get_pocket_xy(self, rc_current_pocket)
            self.params["rc_drop_x"] = drop_x
            self.params["rc_drop_y"] = drop_y

        selected_tool_in_rc = \
            rc_selected_pocket > 0 \
            and rc_selected_pocket <= self.rapidchange.NUM_POCKETS \
            and not self.rapidchange.FORCE_ALL_MANUAL_CHANGES

        do_rc_pickup = \
            self.selected_tool > 0 \
            and selected_tool_in_rc \
            and self.current_tool != self.selected_tool

        do_manual_pickup = \
            self.selected_tool > 0 \
            and not selected_tool_in_rc \
            and self.current_tool != self.selected_tool

        self.params["rc_do_manual_pickup"] = 1 if do_manual_pickup else 0
        self.params["rc_do_rc_pickup"] = 1 if do_rc_pickup else 0

        if do_rc_pickup:
            pickup_x, pickup_y = get_pocket_xy(self, rc_selected_pocket)
            self.params["rc_pickup_x"] = pickup_x
            self.params["rc_pickup_y"] = pickup_y

   #     suppress_probe = do_manual_pickup and self.rapidchange.PROBE_AFTER_MANUAL_LOAD
   #     do_pickup = do_rc_pickup or do_manual_pickup

        do_any_action = \
            do_rc_drop or do_manual_drop \
            or do_rc_pickup or do_manual_pickup 
        
        self.params["rc_do_any_action"] = 1 if do_any_action else 0

        return INTERP_OK
    except Exception as e:
        self.set_errormsg("M6/rapidchange_change_prolog: %s" % (e))
        return INTERP_ERROR

# Prolog for the M290 command, which launches the RapidChange GUI. This is a separate command so that the GUI can be launched from a G-code file without having to do a tool change.
def launch_rack_gui_prolog(self, **words):
    os.environ.setdefault("DISPLAY", ":0")

    try:
        check = subprocess.Popen(
            ["pgrep", "-f", "rack_gui.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if check.wait() == 0:
            # GUI already exists: activate its GTK window.
            try:
                subprocess.call(
                    ["wmctrl", "-a", "RapidChange ATC Pocket Map"]
                )
            except OSError as error:
                self.set_errormsg(
                    "Could not bring Rack GUI forward: %s" % error
                )
                return INTERP_ERROR

            return INTERP_OK

    except Exception as error:
        self.set_errormsg(
            "M290/launch_rack_gui_prolog: %s" % error
        )
        return INTERP_ERROR

    try:
        subprocess.Popen(
            ["python3", "/home/operator/rack_gui.py"],
            close_fds=True
        )
    except Exception as error:
        self.set_errormsg("Could not launch rack GUI: %s" % error)
        return INTERP_ERROR

    return INTERP_OK

# dummy sub to launch the GUI from a G-code file. The actual work is done in the prolog above.
def rack_gui_launch_py(self, **words):
 return INTERP_OK
