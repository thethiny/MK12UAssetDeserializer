import json
import os
import sys
from src.reader import UAssetSerializer

argc = len(sys.argv)

if argc < 2:
    file_in = r"D:\Modding\Git\MK12-UAsset-Manager\files\Consumables.uasset_extract\Raw\Extracted\0_Consumables_b"
    name_table = r"D:\Modding\Git\MK12-UAsset-Manager\files\Consumables.uasset_extract\Parsed\NameTable.txt"
elif argc < 3:
    file_in = sys.argv[1]
    if not os.path.isfile(file_in):
        print("Couldn't find file", file_in)
        exit(1)
    base_dir = os.path.dirname(file_in)
    name_table_file = os.path.basename(file_in) + ".txt"
    name_table = os.path.join(base_dir, name_table_file)
    if not os.path.isfile(name_table):
        print("NameTable not in", base_dir)
        print(f"Either set {name_table_file} next to your file, or provide the NameTable path as the 2nd argument.")
        exit(1)
else:
    file_in = sys.argv[1]
    name_table = sys.argv[2]
    if not os.path.isfile(file_in):
        print("Couldn't find file", file_in)
        exit(1)
    if not os.path.isfile(name_table):
        print("Couldn't find file", name_table)
        exit(1)
    
input_file_name = os.path.basename(file_in)

NAMETABLE = []

with open(name_table, encoding="utf-8") as f:
    for line in f:
        index, name = line.split(": ", 1)
        index = int(index, base=16)
        name = name[:-1] # Remove line end
        NAMETABLE.append(name)
    
with open(file_in, 'rb') as f:
    reader = UAssetSerializer(NAMETABLE, f)
    UAssetContent = UAssetSerializer.ChainDict()
    try:
        while not reader:
            key, value = reader.deserialize()
            UAssetContent[key] = value
        print("Parsing complete!")
    except Exception:
        print("Error at Tell", reader.file_handle.tell())
        raise
        
os.makedirs("parsed", exist_ok=True)
    
with open(f"parsed/{input_file_name}.json", "w+", encoding="utf-8") as f:
    json.dump(UAssetContent, f, ensure_ascii=False, indent=4)


# TODO: Missing ObjectProperty (since I'm setting to Null)
# TODO: Missing TextProperty # Validate: Solution was Arrays behave differently
# TODO: Missing handling when there are actual currency prices so try on gear or something
# TODO: Missing bundles. Edit: Not proper
# TODO: Kollection is not MKInventory so have to re-parse
# TODO: Have to parse Shrine as well