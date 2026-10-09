#  RapidChange Configuration for Tormach PathPilot

Unofficial Tormach PathPilot configuration for https://RapidChangeATC.com type tool changers. Other examples are https://BenchWorks.co.za, https://www.onefinitycnc.com/product-page/onefinity-easy-atc-by-rapidchange-atc-redline and others.

This is a (very) modified version of https://github.com/haskins-guitars/linuxcnc-rapidchange to work with Tormach's PathPilot. It expects an ETS, if any, to be configured and set at the beginning of each run. Even if you use a RapidChange pocket for an ETS, it will be used by the standard PathPilot M37 code.

There is a companion GUI to manage the rack_map, use M290 to load that from the MDI. Because the typical SOP with PathPilot using an ETS requires starting with an empty spindle, manual tool changes can be avoided by loading your RapidChange magazine and then editing the rack_map. 

The whole M6 Remap and related files are structured to minimize the edits required on every PathPilot update. Most of the files reside in ~/gcode sub directories and thus are not impacted by updates.

## Usage

### Tool Table

The Px value from the rack_map.txt file is used to determine which RapidChange pocket to load/unload a tool from. 

Tools not in the rack_map will trigger a manual tool change request. You would be prompted to either remove the tool or insert the tool manually in that case.

Example minimal tool table for an 8 pocket changer.

```
;
T1  P1 ; Tool in pocket 1
T2  P2 ; Tool in pocket 2
T3  P3 ; Tool in pocket 3
T47  P4 ; Tool in pocket 4
T5  P5 ; Tool in pocket 5
T36  P6 ; Tool in pocket 6
T127  P7 ; Tool in pocket 7
T8  P8 ; Tool in pocket 8
T9  P9 ; Tool requiring manual change
T10 P0 ; Tool requiring manual change
```


### G-Code usage

```gcode
; Make sure Px value is set correctly in tool table for each tool.
T1 M6 ; Pickup T1, probe T1
T2 M6 ; Drop T1, pickup T2, probe T2
T0 M6 ; Drop T2
Of course in the case of PathPilot you should be using the ZoomSpeed postprocessor for Fusion360. It will add the M37 ETS code as needed.

; Open dust cover
M64 P[#<_ini[RAPIDCHANGEATC]COVER_DO>]

; Close dust cover
M65 P[#<_ini[RAPIDCHANGEATC]COVER_DO>]

```

## Installation

Copy all files to `rapidchange` directory in your configuration. Recommendation is `/home/operator/rapidchange`.

Copy the .ngc files to ~/gcode/subroutines.

Copy the *.py files to ~/gcode/python, create the directory if it is not present.

Modify 2 existing PathPilot files, you will need to do this every time that you update PathPilot to a new version

```file
#pp_includes ../../../rapidchange/rapidchange.ini at top of `~tmc/configs/tormach_mill/tormach_mill_base.ini`

Add `import * from rc_remap` to `~tmc/configs/tormach_mill/python/remap.py` after the other `import` stements.
```

```inc
Edit the `rapidchange.inc` file as needed. The following is a list of paraments to configure:
```
```
[RAPIDCHANGEATC]
# Set to 1 to force all chnages to be handled manually.
# Set IR_DI to -1 to disable probing after tool change
FORCE_ALL_MANUAL_CHANGES = 0
# Probe tool length after manual tool changes. 1 to enable, 0 to disable
PROBE_AFTER_MANUAL_LOAD = 0

NUM_POCKETS = 8

# Position of pocket #1
POCKET_BASE_X = 580
POCKET_BASE_Y = 100

# Distance between pockets (can be negative values)
POCKET_OFFSET_X = 0
POCKET_OFFSET_Y = 45

# Save Z height
#  Before any XY moves, will G53 G0 Z[#<_ini[RAPIDCHANGEATC]SAFE_Z>] to avoid collisions
#  Usually upper Z limit
SAFE_Z = 194

# RPM when loading
ENGAGE_LOAD_RPM = 1700
# Number of strikes during loading, usually 2, but 3 ok.
ENGAGE_LOAD_STRIKES = 1
# RPM when unloading, usually 300RPM higher than load
ENGAGE_UNLOAD_RPM = 1900
# Number of strikes during unloading, usually 1
ENGAGE_UNLOAD_STRIKES = 2

# Machine Z where nut breaks IR, or nut flush with top of changer
ENGAGE_Z_START = 80
# Machine Z at bottom of engage cycle
#  30mm from top of changer
#  ~34mm from IR break
ENGAGE_Z_END = 50
# Feed rate when engaging changer
ENGAGE_FEED = 2000

# motion.digital-in-xx connected to IR sensor
#   -1 disables IR
IR_DI = 0
# motion.digital-out-xx connected to cover output
#   -1 disables cover
COVER_DO = 0
```

### HAL configuration

There are no Hal file changes required.

### Cover and Tool Detection

In order to make use of these features, you will need a USBIO interface. These are easy to build yourself, using either a Teensy or a ProMicro AT32U4 board plus relay and IR boards. Or you could add a HAL file to map pins on your controller to handle the I/O.

If you decide to embed your ETS inside the Rack, then you will need to edit the Fusion PostProcessor to output the Open and Close commands before and after the M37 call.

### Operation

Typically you start with an empty spindle since PathPilot requires you to touch off the spindle nose on the ETS before using the setter. Since the rack_map file is only read by the tool change code, you must populate it prior to running a job. Use M290 to bring up the editor window.

If a requested tool is not in the rack_map, you will be asked to insert it into the spinlde. Ditto if the tool in the spindle isn't in the rack_map, you will be asked to manually remove it.

It is recommended to use the Setup file feature in Fusion360 to print out the list of tools needed for a job. Alternatively you can see the list at the top when you first load a program.

### Possible Future enhancements

These may or may not happen:
- drop tools into an empty pocket and update the rack_map
- named rack_maps, so you can easily re-run jobs
- visual gui should tools in the rack
