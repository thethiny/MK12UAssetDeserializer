import os
import shutil
import subprocess
from sys import argv
from sys import gettrace

from tqdm import tqdm


def is_debug_mode():
    return gettrace() is not None

DEBUG = is_debug_mode()
ROOT_PATH = "."

if DEBUG:
    INPUT_DIR = os.path.join(ROOT_PATH, "automate_debug")
    TEMP_DIR = os.path.join(ROOT_PATH, "temp_debug")
    if len(argv) == 1:
        argv.append(r"D:\Modding\Git\MK12-UAsset-Manager\out\Release\Binaries\MK12PMan.exe")
else:
    INPUT_DIR = os.path.join(ROOT_PATH, "automate_all")
    TEMP_DIR = os.path.join(ROOT_PATH, "temp")

if len(argv)> 1:
    EXTRACTOR_PATH = argv[1]
else:
    print("Must provide path to the extractor!")
    exit(1)


os.makedirs(TEMP_DIR, exist_ok=True)

files = os.listdir(INPUT_DIR)
i = 0
for file in tqdm(files):
    i += 1
    if not file.endswith(".uasset"):
        continue

    temp_file = os.path.join(TEMP_DIR, file)

    shutil.copy2(os.path.join(INPUT_DIR, file), temp_file)

    # subprocess.run([EXTRACTOR_PATH, temp_file], shell=True, stdout=subprocess.DEVNULL)
    try:
        results = subprocess.check_output([EXTRACTOR_PATH, temp_file], shell=True, errors=None)
        print(results)
    except subprocess.CalledProcessError as e:
        error = str(e).rsplit("exit status", 1)[-1].strip()
        print(f"Error while unpacking uasset file: {error}")
        continue

    file_name = os.path.splitext(os.path.basename(file))[0]
    extract_path = os.path.join(TEMP_DIR, file + "_extract")
    raw_extracted_path = os.path.join(extract_path, "Raw", "Extracted")
    name_table_path = os.path.join(extract_path, "Parsed", "NameTable.txt")

    try:
        for inventory_item in os.listdir(raw_extracted_path):
            copied_file = shutil.copy2(os.path.join(raw_extracted_path, inventory_item), TEMP_DIR)
            name_file = shutil.copy2(name_table_path, f"{TEMP_DIR}/{inventory_item}.txt")
            subprocess.run(["python", "-m", "main_old", copied_file], stdout=subprocess.DEVNULL)
            # os.remove(copied_file)
            # os.remove(name_file)
    except FileNotFoundError:
        continue

    # shutil.rmtree(extract_path)
    # os.remove(temp_file)

# os.removedirs(TEMP_DIR)
