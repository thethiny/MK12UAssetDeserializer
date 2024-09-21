import os

from .reader import UAssetSerializer
from .uasset import UAsset

def extract_uasset(file_path: str, dump_raw: bool = False, dump_parsed: bool = False, dump_loc: str = ""):
    asset = UAsset(file_path, dump_raw, dump_parsed, dump_loc)
    asset.init_uasset()
    for file_name, file_data in asset.exports:
        yield file_name, file_data, asset.name_table

def parse_export(file_name, file_data, name_table):
    print(f"File {file_name} has {len(file_data)} bytes")
    reader = UAssetSerializer(name_table, file_data)
    export_content = UAssetSerializer.ChainDict()
    
    try:
        while not reader:
            key, value = reader.deserialize()
            export_content[key] = value
    except Exception as e:
        raise Exception(f"Error at Tell {reader.file_handle.tell()} for {file_name}: {e}")
    
    print("Parsing Complete")
    return export_content
