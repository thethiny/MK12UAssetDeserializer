from datetime import datetime
import json
import os
import sys

from src.parse import extract_uasset, parse_export
from src.combine import combine, postprocess_dict

argc = len(sys.argv)

if argc < 2:
    print(f"Please provide file or folder to parse")
    exit(1)

in_file = sys.argv[1]

if argc > 2:
    extract_only = sys.argv[2].lower() in ["1", "true", "y", "yes"]
    parse_only = sys.argv[2].lower().strip() == "parse"
else:
    extract_only = parse_only = False

def extract_and_process_uasset(file_path: str, dump_raw: bool = False, dump_parsed: bool = False, dump_loc: str = ""):
    file = os.path.dirname(file_path)
    for file_name, file_data, name_table in extract_uasset(file_path, dump_raw, dump_parsed, dump_loc):
        print(f"Processing export {file_name} for {file}")
        content = parse_export(file_name, file_data, name_table)
        yield file_name, content
        
    print(f"file {file_path} done processing!")

if __name__ == "__main__":
    parsed_save_folder = os.path.join("processed", "parsed")
    extract_folder = os.path.join("processed", "extracted")

    os.makedirs(parsed_save_folder, exist_ok=True)
    os.makedirs(extract_folder, exist_ok=True)

    if not parse_only:
        if os.path.isdir(in_file):
            files = [os.path.join(in_file, f) for f in os.listdir(in_file)]
        else:
            files = [in_file]

        errors = []
        for file in files:
            try:
                for export_name, content in extract_and_process_uasset(file, True, True, extract_folder):
                    with open(os.path.join(parsed_save_folder, export_name + ".json"), "w", encoding="utf-8") as f:
                        json.dump(content, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"Error with {file}")
                print(e)
                errors.append({"file": file, "error": str(e)})

        with open("errors.json", "w", encoding="utf-8") as f:
            json.dump(errors, f, indent=4, ensure_ascii=False)

        if extract_only:
            exit(0)

    global_data = combine(parsed_save_folder, {"Other": {}})
    global_data = postprocess_dict(global_data)

    out_folder = "combined_data"
    os.makedirs(out_folder, exist_ok=True)
    out_file = os.path.basename(in_file.replace("\\", "/").rstrip("/"))
    with open(
        os.path.join(
            out_folder, f"{datetime.now().timestamp()}-{out_file}.json"
        ),
        "w+",
        encoding="utf-8",
    ) as f:
        json.dump(global_data, f, ensure_ascii=False, indent=4)


# TODO: Missing handling when there are actual currency prices so try on gear or something
# TODO: Missing bundles. Edit: Not proper
# TODO: Kollection is not MKInventory so have to re-parse
