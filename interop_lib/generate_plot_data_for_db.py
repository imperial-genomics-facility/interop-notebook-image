import argparse, logging
from interop_data_for_db import generate_data_dumps_and_create_json_for_db

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--run_id', required=True, help='Run name')
parser.add_argument('-r', '--run_path', required=True, help='Path to the run')
parser.add_argument('-o', '--output_dir', required=True, help='Output dir path')
parser.add_argument('-m', '--generate_imaging', default=False, action='store_true', help='Generate imaging data')
parser.add_argument('-d', '--interop_dumptext_exe', default='interop_dumptext', help='Path to InterOp demptext exe')
parser.add_argument('-t', '--interop_imaging_tablet_exe', default='interop_imaging_table', help='Path to InterOp imagig table exe')
args = parser.parse_args()

run_id = args.run_id
run_path = args.run_path
output_dir = args.output_dir
generate_imaging = args.generate_imaging
interop_dumptext_exe = args.interop_dumptext_exe
interop_imaging_tablet_exe = args.interop_imaging_tablet_exe

if __name__=='__main__':
    try:
        generate_data_dumps_and_create_json_for_db(
            run_id=run_id,
            run_path=run_path,
            output_dir=output_dir,
            generate_imaging=generate_imaging,
            interop_dumptext_exe=interop_dumptext_exe,
            interop_imaging_tablet_exe=interop_imaging_tablet_exe)
    except Exception as e:
        logging.error('Failed to generate Interop dump, error: {0}'.format(e))