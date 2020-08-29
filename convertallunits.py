import argparse
import glob
import os
import subprocess
import sys

cwd = os.getcwd()

parser = argparse.ArgumentParser()
parser.add_argument('--input-spec', help=r'search spec for fbi files for units to convert, eg "d:\temp\ccdata\UNITS\*.fbi"')
parser.add_argument('--converter-path', help='path to 3do2scm.exe executable, eg "c:\\3do2scm.exe"')
parser.add_argument('--exporter-path', help='path to supcom-exporter.py, eg "c:\\supcom-exporter.py"')
parser.add_argument('--tadata-paths', help='paths under which to search for 3do files, eg "d:\\temp\\totala1 d:\\temp\\ccdata"', nargs='+')
args = parser.parse_args()

units_dir = os.path.join(cwd,'UNITS')
if not os.path.exists(units_dir):
    os.mkdir(units_dir)

for fn in glob.glob(args.input_spec):
    print("----", fn)
    unit,_ = os.path.splitext(os.path.basename(fn))
    target_dir = os.path.join(units_dir,unit)
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    os.chdir(target_dir)
    
    for suffix in ("", "_dead"):
        cmd = r'{converter_path} {model_name} {tadata_paths} | {python_cmd} {exporter_cmd}'.format(
            converter_path = args.converter_path,
            model_name=unit + suffix,
            tadata_paths=' '.join(args.tadata_paths),
            python_cmd=sys.executable,
            exporter_cmd=args.exporter_path)
        print(cmd)
        os.system(cmd)

os.chdir(cwd)
