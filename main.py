import json
import os
import sys
import math
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
    # UAssetContent = reader.read_struct_property_item()
    try:
        # Normal Reading Part
        root_obj_name = reader.read_fname()
        root_obj_type = reader.read_fname()
        # Reading RowStruct # TODO: Move RowStruct to a handler and manually pass type is RowStruct ObjectProperty
        root_obj_flags = reader.read_int(4)
        root_obj_id = reader.read_int(4)
        _ = reader.read_int(1)
        
        # Reading an ObjectProperty
        root_obj_super = reader.read_int(4, signed=True) # Or flags - Probably
        root_obj_type2 = reader.read_fname()
        file_name = reader.read_fname_class()
        print(f"{root_obj_name}: {root_obj_type} ({root_obj_flags}) #{root_obj_id} [{root_obj_super}] [{root_obj_type2}]")
        print("File Name:", file_name) # Is it?
        root_obj_children_count = reader.read_int(4)
        print("Struct Children", root_obj_children_count)
        
        InventoryItems = {}
        
        for i in range(root_obj_children_count):
            key_name = reader.read_fname()
            current_dict = {}
            cur_fname = reader.read_fname()
            struct_el_count = 0
            while cur_fname != "None": # NOT A CORRECT METHOD BUT A WORKING HACK!
                reader.file_handle.seek(-8, 1)
                struct_el_count += 1
            # for _ in range(7+14): # TODO: Instead of 14, this should be a while != None since objects aren't structured, and move to ObjectProperty Handler
                n, v = reader.read_struct_property_item()
                current_dict[n] = v
                cur_fname = reader.read_fname()
            # _ = reader.read_fname() # None
            InventoryItems[key_name] = current_dict
            print("Read object", key_name, "for a total of", struct_el_count, "elements!")
    except Exception:
        print("Error at Tell", reader.file_handle.tell())
        raise
        
os.makedirs("parsed", exist_ok=True)
    
with open(f"parsed/{input_file_name}.json", "w+", encoding="utf-8") as f:
    json.dump(InventoryItems, f, ensure_ascii=False, indent=4)


# TODO: Missing ObjectProperty (since I'm setting to Null)
# TODO: Missing TextProperty
# TODO: Missing handling when there are actual currency prices so try on gear or something
# TODO: Missing bundles. Edit: Not proper
# TODO: Kollection is not MKInventory so have to re-parse