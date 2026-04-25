# LinuxCNC RapidChange Configuration

Unofficial LinuxCNC configuration for RapidChangeATC tool changer.

Includes an M6 remap, so normal `Tx M6` commands will use RapidChange ATC.

## Usage

### Tool Table

The Px value from the tooltable is used to determine which RapidChange pocket to load/unload a tool from. Other tooltable values are loaded normally.

Tools with Px values less than 1 or greater than `[RAPIDCHANGEATC].NUM_POCKETS` will trigger a manual tool change request.

Example minimal tool table for an 8 pocket changer.

```
;
T1  P1 ; Tool in pocket 1
T2  P2 ; Tool in pocket 2
T3  P3 ; Tool in pocket 3
T4  P4 ; Tool in pocket 4
T5  P5 ; Tool in pocket 5
T6  P6 ; Tool in pocket 6
T7  P7 ; Tool in pocket 7
T8  P8 ; Tool in pocket 8
T9  P9 ; Tool requiring manual change
T10 P0 ; Tool requiring manual change
```

Tx and Px values do NOT need to match, so this is completely valid.

```
;
T123  P1 ; Tool in pocket 1
T456  P2 ; Tool in pocket 2
T789  P9 ; Tool requiring manual change
T1000 P0 ; Tool requiring manual change
```

### G-Code usage

```gcode
; Make sure Px value is set correctly in tool table for each tool.
T1 M6 ; Pickup T1, probe T1
T2 M6 ; Drop T1, pickup T2, probe T2
T0 M6 ; Drop T2

; Open dust cover
M64 P[#<_ini[RAPIDCHANGEATC]COVER_DO>]

; Close dust cover
M64 P[#<_ini[RAPIDCHANGEATC]COVER_DO>]
```

## Installation

Copy all files to `rapidchange` directory in your configuration.

### Add `.ini` file `[RAPIDCHANGEATC]` section

Add `RAPIDCHANGEATC` section and set values for your machine.

```ini
[RAPIDCHANGEATC]
NUM_POCKETS = 8

# Position of pocket #1
POCKET_BASE_X = 583
POCKET_BASE_Y = 99.5

# Distance between pockets (can be negative values)
POCKET_OFFSET_X = 0
POCKET_OFFSET_Y = 45

# Save Z height
#  Before any XY moves, will G53 G0 Z[#<_ini[RAPIDCHANGEATC]SAFE_Z>] to avoid collisions
#  Usually upper Z limit
SAFE_Z = 195

# RPM when loading
ENGAGE_LOAD_RPM = 1500
# Number of strikes during loading, usually 2, but 3 ok.
ENGAGE_LOAD_STRIKES = 1
# RPM when unloading, usually 300RPM higher than load
ENGAGE_UNLOAD_RPM = 1800
# Number of strikes during unloading, usually 1
ENGAGE_UNLOAD_STRIKES = 2

# Machine Z where nut breaks IR, or nut flush with top of changer
ENGAGE_Z_START = 85
# Machine Z at bottom of engage cycle
#  30mm from top of changer
#  ~34mm from IR break
ENGAGE_Z_END = 55
# Feed rate when engaging changer
ENGAGE_FEED = 2000

# motion.digital-in-xx connected to IR sensor
#   -1 disables IR
IR_DI = 0
# motion.digital-out-xx connected to cover output
#   -1 disables cover
COVER_DO = 0

# Toolsetter position
TOOLSET_X = 582.5
TOOLSET_Y = 55

# Feed rate when searching for end of tool
TOOLSET_SEARCH_FEED = 200
# Max distance to search (negative value on most machines)
TOOLSET_SEARCH_DISTANCE = -100
# Backoff distance from search contact to begin latch probe (positive value on most machines)
TOOLSET_LATCH_BACKOFF = 1
# Feed rate when doing more precise latch probe
TOOLSET_LATCH_FEED = 10
# Max distance to do latch probe, should be a little more than (negative value on most machines)
TOOLSET_LATCH_DISTANCE = -1.5
# Machine Z when nut would contact tool setter, used to calculate tool offset
TOOLSET_HEIGHT = 83

# Position to rapid to for manual tool changes
MANUAL_CHANGE_X = 582.5
MANUAL_CHANGE_Y = 0

# motion.digital-out-xx to trigger manual tool change UI
#   -1 disables manual tool changes
TOOL_CHANGE_DO = 1
# motion.digital-in-xx indicating manual tool change complete
#   -1 disables manual tool changes
TOOL_CHANGED_DI = 1
```

### Update `.ini` file `[RS274NGC]` section

Add remap and subroutines to your existing `[RS274NGC]` section.

```ini
[RS274NGC]
REMAP=M6    modalgroup=6 prolog=rapidchange_change_prolog ngc=rapidchange_m6 epilog=change_epilog
SUBROUTINE_PATH = rapidchange/subroutines:~/linuxcnc/nc_files/remap-subroutines
ON_ABORT_COMMAND=o<on_abort> call
```

### Add/update `.ini` file `[Python]` section

#### If you don't have an existing `[Python]` section

1. Add this to your `.ini` file.

```ini
[PYTHON]
TOPLEVEL = rapidchange/toplevel.py
PATH_PREPEND = ./rapidchange/python
PATH_PREPEND = ./rapidchange
PATH_APPEND = ~/linuxcnc/nc_files/examples/remap_lib/python-stdglue
```

#### If you have an existing `[Python]` section

1. Merge the contents of `toplevel.py` and `remap.py` into your existing Python code.
2. Add `PATH_PREPEND = ./rapidchange`.
3. Add `PATH_APPEND = ~/linuxcnc/nc_files/examples/remap_lib/python-stdglue` if it doesn't already exist.

### Update `.ini` file `[HAL]` section

Add `[HAL]HALFILE = rapidchange/atc.hal`, and `[HAL]TWOPASS = on` if you're using `or2` anywhere else.

```ini
[HAL]
HALUI = halui
TWOPASS = on
HALFILE = main.hal
HALFILE = rapidchange/atc.hal
```

### HAL configuration

#### `rapidchange/atc.hal`

Update `rapidchange/atc.hal` to:

1.  Connect IO nets
    - IR (`rapidchange-dust-cover`)
    - Dust cover(`rapidchange-dust-cover`)
    - Tool setter to correct IO pins (`rapidchange-toolsetter`)
2.  If using tool setter, connect `rapidchange-toolsetter` to `motion.probe-input`

    ```
    # If no other probes

    net rapidchange-toolsetter motion.probe-input

    # If other probes

    loadrt or2 names=probes
    addf probes servo-thread
    net rapidchange-toolsetter  probes.in0
    net other-probe             probes.in1
    net any-probe               probes.out => motion.probe-input
    ```

3.  Replace `hal_manualtoolchange` configuration if using another manual tool change UI
