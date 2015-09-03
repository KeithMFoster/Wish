import os
import glob

# RemoveLeftOverFiles
# sometimes there will be files that are just left in the directory. This function is
# to do some house cleanup prior to any run.
def remove_json_files():
    file_list = glob.glob("*.json")
    for f in file_list:
        os.remove(f)