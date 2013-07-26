#!/bin/bash
#: Description: builds the ui for pifacecad_emulator

rcsource="src/pifacecad_emulator.qrc"
rcfile="pifacecad_emulator/pifacecad_emulator_rc.py"
uisource="src/pifacecad_emulator.ui"
uifile="pifacecad_emulator/pifacecad_emulator_ui.py"

printf "Generating resource.\n"
pyside-rcc $rcsource -o $rcfile -py3
printf "Generating UI.\n"
pyside-uic $uisource -o $uifile

# pyside doesn't know about Python submodules
printf "Fixing UI.\n"
string="import pifacecad_emulator_rc"
replace="import pifacecad_emulator.pifacecad_emulator_rc"
sed -e "s/$string/$replace/" $uifile >> /tmp/pifacecad_emulator_ui_file
mv /tmp/pifacecad_emulator_ui_file $uifile