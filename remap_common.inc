# M6/M61 for tool change commands
[REMAP_M6]
modalgroup=6 
argspec=q 
prolog=rapidchange_change_prolog 
ngc=_rapidchange_m6 
epilog=change_epilog

[REMAP_M290]
modalgroup=10 
prolog=launch_rack_gui_prolog
python=rack_gui_launch_py

[REMAP_M61] 
modalgroup=6 
argspec=Q 
prolog=zbotatc_M61_prolog
ngc=tormach_m61
epilog=zbotatc_M61_epilog


# Coolant
[REMAP_M7] 
modalgroup=8 
argspec=pqre 
py=smart_cool_M7

[REMAP_M8] 
modalgroup=8 
argspec=pqre 
py=smart_cool_M8

[REMAP_M9] 
modalgroup=8 
py=smart_cool_M9

[REMAP_M207]
modalgroup=8
py=coolant_through_spindle_pump_on

[REMAP_M208]
modalgroup=8
py=washdown_pump_on

[REMAP_M209]
modalgroup=8
py=all_aux_coolant_off

[REMAP_M210]
modalgroup=8
py=coolant_through_spindle_pump_off

[REMAP_M231]
modalgroup=8
argspec=pq
py=chip_conveyor_on

[REMAP_M233]
modalgroup=8
py=chip_conveyor_off

[REMAP_M264]
modalgroup=8
py=switched_output_on

[REMAP_M265]
modalgroup=8
py=switched_output_off

[REMAP_M80]
modalgroup=7
py=save_user_modals_M80

[REMAP_M81]
modalgroup=7
py=restore_user_modals_M81

[REMAP_M82]
modalgroup=10
py=restore_remap_start_line_state

[REMAP_M83]
modalgroup=10
py=clear_remap_start_line_state

[REMAP_G30]
modalgroup=1   
argspec=xyza 
py=g300

[REMAP_M998]
modalgroup=5 
argspec=xyza 
py=m998

[REMAP_G50]
modalgroup=1
py=g500

[REMAP_G47]
modalgroup=1 
argspec=xyZpqRd 
py=g470

[REMAP_G73]
modalgroup=1
argspec=rpqijklxyzadef
prolog=peck_drilling_cycle_prolog
py=g730

[REMAP_G83]
modalgroup=1
argspec=rpqfijklxyzadef
prolog=peck_drilling_cycle_prolog
py=g830

[REMAP_G74] 
modalgroup=1 
argspec=rpijkxyza 
prolog=tapping_cycle_prolog 
py=g740

[REMAP_G84] 
modalgroup=1 
argspec=rpijkxyza 
prolog=tapping_cycle_prolog 
py=g840

[REMAP_G37]
modalgroup=1
argspec=hpexyz
prolog=g370_prolog
ngc=g370remap
epilog=g370_epilog

[REMAP_G37.1]
modalgroup=1
argspec=xyz
prolog=g370_prolog
ngc=g371remap

[REMAP_M301]
modalgroup=10
py=start_video_recording_M301

[REMAP_M302]
modalgroup=10
py=stop_video_recording_M302

[REMAP_M303]
modalgroup=10
py=take_picture_M303

[REMAP_G39.2]
modalgroup=1
argspec=adelqxyz
prolog=g39x_prolog
py=g392

#Callback at program stop
[REMAP_M740]
modalgroup=11
ngc=m740remap
