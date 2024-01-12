import json
import os
import re

character_stuff_re = re.compile(r"(?:Character|Kameo)-?(.+\b)")
gear_parse_re = re.compile(r"(.+)_Gear(\d+)(?:_(.+))?")
player_module_re = re.compile(r"(F|B)G_([A-Za-z]+)(_.+)+")
character_skin_re = re.compile(r"([A-Za-z]+)_Skin(\d+)(.*)")

global_data = {"unknown": {}}

ALLOWED_CATEGORIES = set([
    "Fatality",
    "Brutality",
    "Announcer",
    "Skin",
    "Gear",
    "Bundle",
    "Consumable",
    "Environment",
    "Ladder-Ending",
    "PlayerModule",
    "Taunt"
])

CHARACTERS = set([
    "Ashrah",
    "Baraka",
    "Geras",
    "Havik",
    "JohnnyCage",
    "Kenshi",
    "Kitana",
    "KungLao",
    "LiMei",
    "LiuKang",
    "Mileena",
    "Nitara",
    "Raiden",
    "RainMage",
    "Rain",
    "Reiko",
    "Reptile",
    "Scorpion",
    "ShangTsung",
    "ShaoKahn",
    "GeneralShao",
    "Sindel",
    "Smoke",
    "SubZero",
    "Tanya",
    # DLC
    "OmniMan",
    "QuanChi",
    "PeaceMaker",
    "Ermac",
    "Homelander",
    "Takeda",
    # Leaked DLC
    "Cyrax",
    "Sektor",
    "Noob",
    "Jade",
    "CassieCage",
    "KungJin",
    "JacquiBriggs",
])

KAMEOS = set([a + "KAM" for a in [
    "Darrius",
    "Sareena",
    "Cyrax",
    "Kano",
    "Sonya",
    "Sektor",
    "Frost",
    "Jax",
    "Stryker",
    "Scorpion",
    "SubZero",
    "KungLao",
    "Shujinko",
    "Motaro",
    "Goro",
    # DLC
    "Tremor",
    "Khameleon",
    "JohnnyCage",
    "JanetCage",
    "Mavado",
    "Ferra"
]])

RARITIES = {
    "None": "Default",
    "Rarity1": "Common",
    "Rarity2": "UnCommon",
    "Rarity3": "Rary",
    "Rarity4": "Very Rare",
    "Rarity5": "Ultra Rare"
}

def parse_rarity(rarity):
    return RARITIES.get(rarity, "Unknown")

for root, folders, files in os.walk("parsed"):
    for file in files:
        print("Parsing file", file)
        file_path = os.path.join(root, file)
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            data = data.get("RowStruct", None) or data.get("LootTable", None)
            if data is None:
                raise Exception(f"Couldn't determine data type!")
            
        for item_id, item_dict in data.items():
            translation_id, translation_default = item_dict.get("Title") or [None, None]
            requirement_trans_id, requirement_trans_default = item_dict.get("UnlockRequirement") or [None, None]
            rarity = item_dict.get("Rarity", {}).get("value", "")
            rarity = rarity.rsplit("::", 1)[-1]
            rarity = parse_rarity(rarity)
            
            max_allowed = item_dict.get("MaxCount", 1)
            
            bundled_items = item_dict.get("BundledItems", [])
            bundled_items = [item["RowName"] for item in bundled_items]
            
            categorized_dict = global_data["unknown"] # Fallback
            tags = set(item_dict.get("Tags", []))
            tags |= set(item_dict.get("InternalTags", []))
            character = item_dict.get("Character", {}).get("RowName")
            
            if not character:
                characters = CHARACTERS & tags
                if len(characters) > 1:
                    print(f"Found more than character in item {item_id}!")
                    exit()
                if characters:
                    character = characters.pop()
            
            if not character:
                characters = KAMEOS & tags
                if len(characters) > 1:
                    print(f"Found more than character in item {item_id}!")
                    exit()
                if characters:
                    character = characters.pop()

            if character not in tags and character:
                print(f"Warning! Character {character} is not in tags. Undefined behavior!")
                print(f"item id {item_id} in file {file}")
                exit()
            
            found_type = None
            type_dict = {}
            for tag in tags:
                category = character_stuff_re.match(tag)
                if category:
                    category = category.group(1)
                    type_dict = global_data.setdefault(category, {})
                    if not character:
                        print(f"Warning! Character Subtag {category} with no Character!")
                        exit()
                    categorized_dict = type_dict.setdefault(character, {})
                    found_type = category
                    break # One tag only
                elif tag in ALLOWED_CATEGORIES:
                    type_dict = global_data.setdefault(tag, {})
                    if character: # Character stuff or seasonal
                        category = character
                    else:
                        category = "Shared"
                    categorized_dict = type_dict.setdefault(category, {})
                    found_type = tag
                    # break # Allow to be overridden by character tag
            if found_type is None:
                print(f"Item {item_id} has no allowed tags!", tags)
                # Replace later with `Unknown` category
                
            small_icon = item_dict.get("PreviewIcon", "None")
            large_icon = item_dict.get("LargePreviewIcon", "None")
            
            if found_type == "PlayerModule":
                if small_icon == large_icon == "None":
                    large_icon = item_dict.get("Asset", "None")
                found = player_module_re.match(item_id)
                if found:
                    character = found.groups()[1]
                    categorized_dict = type_dict.setdefault(character, {})
                       
            icons = {
                "small": small_icon,
                "large": large_icon,
            }
            
            color_swatch = item_dict.get("ColorPaletteSwatch", {}).get("Colors")
            
            itemSlug = item_id
            if len(itemSlug.rsplit(".", 1)) > 1: # Deprecated
                slug, _id = itemSlug.rsplit(".", 1)
                itemSlug = f"{slug}_{int(_id)-1}"
            
            object = {
                "id": item_id, #{
                    #"itemSlug": itemSlug,
                    #"itemId": item_id,
                #},
                "name": {
                    "localizationId": translation_id,
                    "default": translation_default
                },
                "unlockRequirements": {
                    "localizationId": requirement_trans_id,
                    "default": requirement_trans_default
                },
                "rarity": rarity,
                "previewImages": icons,
                "colors": color_swatch,
                "bundledItems": bundled_items,
                "max": max_allowed,
                "origin": file.split("_", 1)[-1].rsplit("_", 1)[0]
            }
            
            if found_type == "Gear":
                found = gear_parse_re.match(item_id)
                if not found:
                    raise ValueError(f"Couldn't parse gear {item_id}!")
                owner_char, gear_id, gear_pattern = found.groups()
                categorized_dict.setdefault(gear_id, {})[item_id] = object
            elif found_type == "Skin":
                found = character_skin_re.match(item_id)
                if not found:
                    raise ValueError(f"Couldn't parse skin {item_id}")
                owner_char, skin_id, skin_pattern = found.groups()
                categorized_dict.setdefault(skin_id, {})[item_id] = object
            else:
                categorized_dict[item_id] = object
                
def postprocess_dict(dictionary):
    if isinstance(dictionary, dict):
        d = {}
        for k, v in sorted(dictionary.items()):
            if v == "None":
                v = None
            d[k] = postprocess_dict(v)
        return d
    else:
        return dictionary
    
global_data = postprocess_dict(global_data)
                
with open("all_parsed_data.json", "w+", encoding="utf-8") as f:
    json.dump(global_data, f, ensure_ascii=False, indent=4)