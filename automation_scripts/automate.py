import os
import shutil
import subprocess
from sys import argv

ROOT_PATH = "."

if len(argv)> 1:
    EXTRACTOR_PATH = argv[1]
else:
    print("Must provide path to the extractor!")
    exit(1)

INPUT_DIR = os.path.join(ROOT_PATH, "automate_all")
TEMP_DIR = os.path.join(ROOT_PATH, "temp")

os.makedirs(TEMP_DIR, exist_ok=True)

files = os.listdir(INPUT_DIR)
i = 0
for file in files:
    i += 1
    if not file.endswith(".uasset"):
        continue
    
    print(f"{i}/{len(files)}")
    
    temp_file = os.path.join("temp", file)
    
    shutil.copy2(os.path.join(INPUT_DIR, file), temp_file)

    subprocess.run([EXTRACTOR_PATH, temp_file], shell=True, stdout=subprocess.DEVNULL)
    
    file_name = os.path.splitext(os.path.basename(file))[0]
    extract_path = os.path.join(TEMP_DIR, file + "_extract")
    raw_extracted_path = os.path.join(extract_path, "Raw", "Extracted")
    name_table_path = os.path.join(extract_path, "Parsed", "NameTable.txt")
    
    for inventory_item in os.listdir(raw_extracted_path):
        copied_file = shutil.copy2(os.path.join(raw_extracted_path, inventory_item), TEMP_DIR)
        name_file = shutil.copy2(name_table_path, f"{TEMP_DIR}/{inventory_item}.txt")
        subprocess.run(["python", "-m", "main", copied_file], stdout=subprocess.DEVNULL)
        # os.remove(copied_file)
        # os.remove(name_file)

    shutil.rmtree(extract_path)
    # os.remove(temp_file)

# os.removedirs(TEMP_DIR)
    