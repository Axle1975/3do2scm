rem This script packages the python side of the app into an exe.
rem You still need to build the c++ side using cmake
rem
rem NB you need pyinstaller (a python util) on your path. eg by activating a virtualenv.
pyinstaller -F convertallunits.py
pause