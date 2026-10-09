# Some of this code is from the Tormach Tool Change remap, which is licensed under the GNU General Public License v3.0. See
# And some is from https: // github.com/haskins-guitars/linuxcnc-rapidchange
# stuck together by Gerrit V.
# pylint: disable=import-error
from interpreter import *
import linuxcnc
import os
from json import tool
import subprocess
from posixpath import devnull
throw_exceptions = 1


def init_rapidchange(self):
   self.rapidchange = RapidChangeConfig()


class RapidChangeConfig:
    def __init__(self):
        # Read RapidChange values from ini file once at startup
        self.inifile = linuxcnc.ini(os.environ['INI_FILE_NAME'])

        self.FORCE_ALL_MANUAL_CHANGES = self.read_ini_value_bool(
            "FORCE_ALL_MANUAL_CHANGES")

        self.POCKET_BASE_X = self.read_ini_value("POCKET_BASE_X")
        self.POCKET_BASE_Y = self.read_ini_value("POCKET_BASE_Y")
        self.POCKET_OFFSET_X = self.read_ini_value("POCKET_OFFSET_X")
        self.POCKET_OFFSET_Y = self.read_ini_value("POCKET_OFFSET_Y")
        self.NUM_POCKETS = self.read_ini_value("NUM_POCKETS")

        

        # Load the rack mapping
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
        return self.rack_map.get(tool, 0)

    # Calculate X/Y position of given pocket


    def get_pocket_xy(self, pocket):
        x = self.POCKET_BASE_X + \
            self.POCKET_OFFSET_X * (pocket - 1)
        y = self.POCKET_BASE_Y + \
            self.POCKET_OFFSET_Y * (pocket - 1)

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
    if self.task == 0:  # from remap.py zbotatc_M6_prolog
        # this is the preview that is run when the file is loaded
        # because we remapped M6, the python GLCanon.change_tool() method is never called.
        # but we want to use that to easily build a list of all tools that are used within a program
        # at preview time.  So drive this callback manually during preview and let that side of things keep track
        # of it since it will know when the preview is complete after the load (and we don't).
        self.params["selected_tool"] = self.selected_tool
        emccanon.CHANGE_TOOL()
        return INTERP_OK

    # trick to get RapidChange init'd without modifying PP's toplevel and remap.py modules. This is a bit of a hack, but it works.
    if not hasattr(self, "rapidchange"):
        init_rapidchange(self)
        # Setup a bunch of Globals for use in ngc files
        self.params["_rc_engage_load_rpm"] = self.rapidchange.read_ini_value("ENGAGE_LOAD_RPM")
        self.params["_rc_engage_load_strikes"] = self.rapidchange.read_ini_value("ENGAGE_LOAD_STRIKES")
        self.params["_rc_engage_unload_rpm"] = self.rapidchange.read_ini_value("ENGAGE_UNLOAD_RPM")
        self.params["_rc_engage_unload_strikes"] = self.rapidchange.read_ini_value("ENGAGE_UNLOAD_STRIKES")
        self.params["_rc_engage_Z_start"] = self.rapidchange.read_ini_value("ENGAGE_Z_START")
        self.params["_rc_engage_Z_end"] = self.rapidchange.read_ini_value("ENGAGE_Z_END")
        self.params["_rc_engage_Z_IR_nut_break"] = self.rapidchange.read_ini_value("ENGAGE_Z_IR_NUT_BREAK")
        self.params["_rc_engage_feed"] = self.rapidchange.read_ini_value("ENGAGE_FEED")
        self.params["_rc_IR_DI"] = self.rapidchange.read_ini_value("IR_DI")      
        self.params["_rc_cover_D0"] = self.rapidchange.read_ini_value("COVER_DO")
        #self.params["_rc_rack_table"] = self.rapidchange.read_ini_string("RACK_TABLE")
        # self.params["_rc_rack_map"] = self.rapidchange.RACK_MAP
        self.params["_rc_num_pockets"] = self.rapidchange.read_ini_value("NUM_POCKETS")
        self.params["_rc_tool_changer_enabled"] = not self.rapidchange.read_ini_value("FORCE_ALL_MANUAL_CHANGES")

    # reload the mapping file everytime, just in case it has changed since the last time we used it
    self.rack_map = self.rapidchange.load_rack_map()

    if self.cutter_comp_side > 0:
        self.set_errormsg(
            '::::Cannot change tools with cutter radius compensation on')
        return INTERP_ERROR

    # Check for epilog retract to restore Z to same position at the start of m6
    # if it was above tool change position.
    """ TODO decide if need this 
    self.params["_m6_epilog_retract"] = 1.0   # enabled by default
    m6epilog_retract = self.redis.hget('zbot_slot_table', 'm6_epilog_retract')
    if m6epilog_retract == 'False':
        self.params["_m6_epilog_retract"] = 0.0  # disabled """

    try:
        # get old tool and new tools set up
        self.params["_old_tool"] = self.params["_current_tool"]
        self.params["_new_tool"] = self.selected_tool
        if self.params["_old_tool"] == -1:
            self.params["_old_tool"] = 0  # little quirk of lcnc at startup

        # OK lets see if tray load positon requested - always M6 T0 Q-1
        """ 
        TODO Not sure we need this
        if 'q' in words and words['q'] == -1.0 and self.params["_new_tool"] == 0.0:
            self.params["_go_to_tray_load"] = 1.0
            self.error_handler.log(
                "Tool Change - Go To Tray Load Requested from UI")
        else:
            self.params["_go_to_tray_load"] = 0.0 """
        
        self.params["_go_to_tray_load"] = 0.0 # TODO fake the tray load for now, until we have a UI to request it
        if self.params["_new_tool"] == self.params["_old_tool"] and self.params["_go_to_tray_load"] != 1.0:  # just exit - do nothing in NGC , just M5
            self.error_handler.log(
                "Tool Change is effectively a no-op as new and old tool are same {}".format(self.params["_new_tool"]))
            # set mode to exit NGC procedure which REMAP will now call
            self.params["_mode"] = -1.0
            return INTERP_OK  # will now pass control to NGC, which will exit

       
        # default neither tool is in the rack
        self.params["_old_tool_in_rack"] = False
        self.params["_new_tool_in_rack"] = False

        # populate_rack_pocket_data(self)
        self.rapidchange.rack_map = self.rapidchange.load_rack_map()

        self.error_handler.log("rc_remap.py - Current Tool: {}  Selected Tool: {}".format(
            self.params["_old_tool"], self.params["_new_tool"]))
        # we now have the old and new tool number and the data for all the pockets
        # look for old and new tool number in the pocket data
        # Get Px values from tool table for current and selected tools
        # Get RapidChange pockets from rack map
        rc_current_pocket = self.rapidchange.find_rack_pocket(self.params["_old_tool"])
        rc_selected_pocket = self.rapidchange.find_rack_pocket(self.params["_new_tool"])

        if rc_current_pocket != 0 and self.params["_old_tool"] != 0.0:
            self.params["_old_tool_in_rack"] = True

        if rc_selected_pocket != 0 and self.params["_new_tool"] != 0.0:
            self.params["_new_tool_in_rack"] = True
        
        drop_x, drop_y = self.rapidchange.get_pocket_xy(rc_current_pocket)
        self.params["_rc_drop_x"] = drop_x
        self.params["_rc_drop_y"] = drop_y

        pickup_x, pickup_y = self.rapidchange.get_pocket_xy(rc_selected_pocket)
        self.params["_rc_pickup_x"] = pickup_x
        self.params["_rc_pickup_y"] = pickup_y
        
        # no mill ATC enabled
        #if toolchange_type == MILL_TOOLCHANGE_TYPE_REDIS_MANUAL:
         #   for i in range(self.atc_tray_tools):
          #      self.pocket_dict[str(i)] = '0'

        # ---------------------------------------------------------
        #        find pockets from imported redis data
        # ---------------------------------------------------------
        #self.atc_tray_tools = self.hal["atc-tools-in-tray"]
        # print self.hal["atc-tools-in-tray"],"TOOLS IN TRAY FROM REMAP"
        self.params["_old_slot"] = -1.0  # not found default
        self.params["_new_slot"] = -1.0  # not found defalut

        """ for ix in range(self.atc_tray_tools):  # run the tray
            if self.params["_new_tool"] != 0.0 and self.pocket_dict[str(ix)] == stringed_new_tool:
                self.params["_new_slot"] = float(ix)
            if self.params["_old_tool"] != 0.0 and self.pocket_dict[str(ix)] == stringed_old_tool:
                self.params["_old_slot"] = float(ix) """

        if self.params["_new_tool"] != 0.0 and rc_selected_pocket !=0:
            self.params["_new_slot"] = rc_selected_pocket
        if self.params["_old_tool"] != 0.0 and rc_current_pocket !=0:
            self.params["_old_slot"] = rc_current_pocket

        # Manual changes have no slots for new or old, even if atc is active - it's the same
        # Go to tray load when T0 is active comes here too because there is no stow or fetch
        # operation needed. In this case we force it through the auto change anyway
        if (self.params["_old_slot"] == -1 and self.params["_new_slot"] == -1)\
        and (self.params["_go_to_tray_load"] != 1.0):

            # set mode for NGC procedure to only prompt in
            self.params["_mode"] = -1.0
            print ("remap - manual tool change initiated")

            self.error_handler.log("Prepare for upcoming Tool Change (Manual) - New Tool {}  Old Tool {}".format(
                self.params["_new_tool"],
                self.params["_old_tool"]))

            return INTERP_OK  # pop right out since no automation is required

        # for testing and debugging
        self.error_handler.log("Prepare for upcoming Tool Change (ATC) - New Tool {} [{}]  Old Tool {} [{}] ".format(
            self.params["_new_tool"], self.params["_new_slot"],
            self.params["_old_tool"], self.params["_old_slot"] ))

        # Some internal housekeeping for ATC
        # see if Z axis is homed, and tool change location reasonable

        
        # tells NGC to execute full auto procedure
        self.params["_mode"] = 0
        print ("remap - auto change initiated")

        return INTERP_OK

    except Exception as e:
        #traceback_txt = traceback.format_exc()
        #self.error_handler.log("Exception in M6 prolog.  {}".format(traceback_txt))
        self.set_errormsg("M6/change_prolog: %s" % (e))
        return INTERP_ERROR


def zbotatc_M6_epilog(self, **words):
    self.set_tool_parameters()   # interp -  loads defaults for T0 in tool table
    self.toolchange_flag = True  # interp -  so interpreter why the flush happened
    yield INTERP_EXECUTE_FINISH  # interp -  this actuallty executes all q entries
    yield INTERP_OK              # now finally go away


    
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
             ["python3", "/home/operator/gcode/python/rack_gui.py" , self.rapidchange.RACK_TABLE, str(int(self.rapidchange.NUM_POCKETS))],
             close_fds=True
        )
    except Exception as error:
        self.set_errormsg("Could not launch rack GUI: %s" % error)
        return INTERP_ERROR

    return INTERP_OK

# dummy sub to launch the GUI from a G-code file. The actual work is done in the prolog above.


def rack_gui_launch_py(self, **words):
 return INTERP_OK
