import os
import subprocess
import shutil
import pandas as pd
import numpy as np

# Transfer the  TOT_RUNOFF files to the correct directory
# Run the model in using a subprocess
# Append the results from that CSV to a new CSV with a new file name

model_name = "merced"
model_folder = "Merced_Climate"
model_run_script = "run_merced_model.py"
climate_change_folder = "Climate Change"
climate_change_dest = "s3_imports"

bucket = 'openagua-networks'
dest = os.getcwd() + "\\" + model_folder + "\\" + model_name + "\\" + climate_change_dest
root_dir = os.path.join(os.getcwd(), model_name)
model_path = os.path.join(root_dir, 'pywr_model.json')
network_key = os.environ.get('NETWORK_KEY')
final_csv = None

def add_data(final_csv, prefix):
    results_csv = pd.read_csv(os.getcwd() + "\\" + model_folder + "\\" + model_name + "\\" + "results.csv")
    results_csv = results_csv.add_prefix(prefix + "/")
    if final_csv is None:
        final_csv = results_csv
    else:
        final_csv = final_csv.join(results_csv)
    return final_csv

def run_model():
    os.chdir(os.getcwd() + "\\" + model_folder)
    proc = subprocess.run(['python', os.getcwd() + "\\" + model_run_script,
                           model_path, root_dir, bucket, network_key], stdout=subprocess.PIPE)


# Get all folders in climate change
folder_names = next(os.walk(os.getcwd() + "\\" + climate_change_folder))[1]

for folder in folder_names:
    # Copy the Runoff files to the model
    src_files = os.listdir(os.getcwd() + "\\" + climate_change_folder + "\\" + folder)
    for file_name in src_files:
        file_path = os.path.joisn(os.getcwd() + "\\" + climate_change_folder + "\\" + folder, file_name)
        shutil.copy(file_path, dest)

    # Run the model
    print("Running Model " + str(folder))
    run_model()
    os.chdir("..")
    prefix = folder
    final_csv = add_data(final_csv, prefix)

final_csv.to_csv(os.getcwd() + "\\climate_change.csv")
