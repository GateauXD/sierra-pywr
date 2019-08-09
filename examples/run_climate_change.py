import os
import subprocess
import shutil
import pandas as pd
import numpy as np

# Transfer the  TOT_RUNOFF files to the correct directory
# Run the model in using a subprocess
# Append the results from that CSV to a new CSV with a new file name

model_name = "merced"
model_folder = "Merced_Climate`"
model_run_script = "run_merced_model.py"
climate_change_folder = "Climate Change"
climate_change_dest = "s3_imports"

bucket = 'openagua-networks'
dest = os.getcwd() + "\\" + model_folder + "\\" + model_name + "\\" + climate_change_dest
root_dir = os.path.join(os.getcwd(), model_name)
model_path = os.path.join(root_dir, 'pywr_model.json')
network_key = os.environ.get('NETWORK_KEY')

def add_csv():
    pass
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
        file_path = os.path.join(os.getcwd() + "\\" + climate_change_folder + "\\" + folder, file_name)
        shutil.copy(file_path, dest)

    # Run the model
    run_model()
    os.chdir("..")

