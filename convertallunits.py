import glob
import os
import subprocess

cwd = os.getcwd()

units_dir = os.path.join(cwd,'UNITS')
if not os.path.exists(units_dir):
    os.mkdir(units_dir)

for fn in glob.glob('d:/temp/ccdata/UNITS/*.fbi'):
    print "----", fn
    unit,_ = os.path.splitext(os.path.basename(fn))
    target_dir = os.path.join(units_dir,unit)
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    os.chdir(target_dir)
    cmd = r'd:\wrk\3do2scm\build_vs2019\app\Debug\3do2scm.exe {} | python d:\wrk\3do2scm\source\scm\supcom-exporter.py'.format(unit)
    os.system(cmd)
    cmd = r'd:\wrk\3do2scm\build_vs2019\app\Debug\3do2scm.exe {} | python d:\wrk\3do2scm\source\scm\supcom-exporter.py'.format(unit+"_dead")
    os.system(cmd)


os.chdir(cwd)
