# Steps

_Make sure to run all files from the root folder and not from automation_scripts_

1. Open FModel, and set the filter to `/Inventory/` and select all files.
2. Export all of the files.
3. Run [get_all_files.ps1](/automation_scripts/get_all_files.ps1) with the path to the exported folder's root.
4. All files are now in `automate_all` folder, with some non-required files but no problem, they will be ignored.
5. Run [automate.py](/automation_scripts/automate.py) and specify the [MK12 Package Manager](https://github.com/thethiny/MK12PMan) executable path.
6. You must now have a folder called parsed that contains your json files.
7. Run [parse_combiner.py](/parse_combiner.py) to combine all json files into one cleaned & categorized.