import argparse
import glob
import json
import os
import scm.supcom_exporter 
import subprocess
import sys

cwd = os.getcwd()

parser = argparse.ArgumentParser()
parser.add_argument('--input-spec', help=r'search spec for fbi files for units to convert, eg "d:\temp\ccdata\UNITS\*.fbi"')
parser.add_argument('--converter-cmd', help='path to 3do2scm.exe executable, eg "c:\\3do2scm.exe"', required=False, default=os.path.join(cwd,"3do2scm.exe"))
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
        try:
            json_bytes = subprocess.check_output([args.converter_cmd, unit+suffix] + args.tadata_paths, stderr=None, shell=True)
            if json_bytes:
                _3do_data = json.loads(json_bytes)
                scm.supcom_exporter.export(_3do_data)
        except subprocess.CalledProcessError as e:
            print("Unable to convert model: {}".format(unit+suffix))

os.chdir(cwd)
