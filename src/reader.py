from io import BufferedReader, BytesIO
import re
import struct
from typing import Any, List, Optional, Union

INT_PACK_DICT = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}
FLOAT_PACK_DICT = {4: 'f', 8: 'd'}

class UAssetSerializer:

    SUPPORTED_CLASSES = {
        "RowStruct",
        "mLootStruct"
    }
    SUPPORTED_STRUCTS = {  # No longer needed as everything is now automated
        "ColorPaletteSwatch",  # 4
        "MKInventoryItemPrice",  # 3
        "MKInventoryDataTableRowHandle",  # 2
        "MKInventoryItemDefinitionGroupWithAsset",  # 1
        "MKLootTable",  # 2
        "MKLootTableDropItem",  # 5
        "MKLootDropItemPicker",  # 1
        "MKLootDropItemPrerequisitePicker",  # 1
        "MK12InventoryLootItem",  # 4
        "CharacterLibraryAssetEntry",  # 6
        "DateTime",
        "Color",
        "Timespan",
    }

    SUPPORTED_ENUMS = {
        0: "value",
        8: "class",
    }

    _SUPPORTED_READ_MODES = Union[BufferedReader, bytes]

    INT_PROPERTY_RE = re.compile(r"(U)?Int(\d*)Property")

    class ShallowReadIO:
        def __init__(self, data: bytes):
            self.data = data
            self.cursor: int = 0
            self.size = len(self.data)

        def tell(self):
            return self.cursor

        def seek(self, offset, reference = 0):
            if reference == 0:
                if offset < 0 or offset >= self.size:
                    raise ValueError(f"Out of bounds for ReadIO!")
                self.cursor = offset
            elif reference == 1:
                self.cursor += offset
                if 0 > self.cursor >= self.size:
                    raise ValueError(f"Out of bounds for ReadIO!")
            elif reference == 2:
                if offset > 0 or (-offset) > self.size:
                    raise ValueError(f"Out of bounds for ReadIO!")
                self.cursor = self.size + offset
            else:
                raise ValueError(f"No reference point {reference}")

        def read(self, size = -1):
            if size == 0:
                return b""
            if size == -1:
                data = self.data[self.cursor:]
                self.cursor = self.size
                return data
            if size < 0:
                raise ValueError(f"Cannot read negative size!")
            if size + self.cursor > self.size:
                raise ValueError(f"Out of bound while reading {size} bytes from {self.cursor}")

            data = self.data[self.cursor:self.cursor+size]
            self.cursor += size
            return data

    def __init__(self, nametable: List[str] = [], reader: Optional[_SUPPORTED_READ_MODES] = None):
        if nametable:
            self.set_nametable(nametable)
        if reader:
            self.set_reader(reader)

    def set_nametable(self, nametable):
        self.nametable = nametable

    def set_reader(self, reader: _SUPPORTED_READ_MODES):
        self.file_handle: Union[UAssetSerializer.ShallowReadIO, BufferedReader]
        if isinstance(reader, bytes):
            self.file_handle = self.ShallowReadIO(reader)
        else:
            self.file_handle = reader # type: ignore
        self.__init_reader()

    def __init_reader(self):
        self.file_handle.seek(0, 2)
        self.file_size = self.file_handle.tell()
        self.file_handle.seek(0)

    def __bool__(self):
        return self.file_handle.tell() == self.file_size

    def tell(self):
        return hex(self.file_handle.tell())

    @property
    def _tell(self):
        return self.file_handle.tell()

    def deserialize(self,):
        return self.read_property_once()

    def number_to_fname(self, number, suffix = 0):
        name = self.nametable[number]
        if suffix:
            # Noticed that all items start at 2 instead of 0, so BG_Ashrah.2 is actually BG_Ashrah_1
            name += f"_{suffix-1}"  # Enable if you want
            # name += f".{suffix}" # Enable if you want
        return name

    # Reads
    def read_fname(self):
        name = self.read_int(4, endianness="le", signed=False)
        name_suffix = self.read_int(4, endianness="le", signed=False)
        name = self.number_to_fname(name, name_suffix)
        return name

    def read_obj_reference(self):
        ref_idx = self.read_int(4, endianness="le", signed=True)
        ref_name = abs(ref_idx)+1
        try:
            name = self.nametable[ref_name]
            return f"Object {'-' if ref_idx < 0 else ''}0x{abs(ref_idx):X}: {name}"
        except IndexError:
            return f"[ref:={ref_idx:X}|{ref_name:X}]"

    def read_fname_class(self): # Classes are signed and negative
        name = self.read_int(4, endianness="le", signed=True)
        if name < 0:
            name -= 1 # Python rindex
        return self.nametable[name]

    def read_int(self, size, endianness='le', signed = False):
        endianness = endianness.lower()
        endianness = '<' if "le" else '>'
        b_size = INT_PACK_DICT.get(size, '')
        format_str = endianness + (b_size.lower() if signed else b_size)
        data = self.file_handle.read(size)
        return struct.unpack(format_str, data)[0]

    def read_float(self, size):
        format_str = '<' + FLOAT_PACK_DICT.get(size, '')
        data = self.file_handle.read(size)
        return struct.unpack(format_str, data)[0]

    def read_string(self, size = None):
        string_size = size if size is not None else self.read_int(4, signed=True)
        if string_size < 0:
            string_size *= -2
            encoding = "utf-16"
        else:
            encoding = "utf-8"
        string = self.file_handle.read(string_size).decode(encoding)
        ret_str = ''
        for s in string:
            if s == '\x00':
                break
            ret_str += s
        return ret_str

    def read_property_once(self, loop_count = 1):
        property_name = self.read_fname()
        if property_name == "None":
            property_reference = self.read_int(4)
            if property_reference != 0:
                print (f"Warning: Encountered Unknown Property `None` with size {property_reference} not 0! Undefined Behavior! Expect Crashes!")
                self.file_handle.seek(-4 -8, 1)
                # This is very new! I have no idea what this breaks!
            return "", None # Sometimes ObjectProperty has None (0x8), SomeClass (0x4) after it and idk why or when
        property_type = self.read_fname()
        # print(f"{property_name=} | {property_type}")
        property_value = self.read_data_as_type(property_type, property_name, loop_count)
        return property_name, property_value

    # Properties
    def read_bool_property(self, from_array = False):
        if from_array:
            return self.read_int(1) == 1
        size = self.read_int(8)
        value = self.read_int(1)
        _ = self.file_handle.read(1)
        return value == 1

    def read_byte_property(self, from_array = False):
        if from_array:
            byte_type = self.read_fname()
            if byte_type == "None":
                return self.read_int(1)
            return self.read_fname()
        size = self.read_int(8) # idk if this is size or object counts since a byte is one bye lol
        byte_type = self.read_fname()
        _ = self.file_handle.read(1)
        # value = self.read_int(size) # Either once of size `size` or size entries of fname of size 1 each, or completely different. Idk for now. Maybe if it's NONE then you read 1 byte, but if it's not None then you read 8 bytes and that is subtype.
        # return value
        if byte_type == "None":
            return self.read_int(size)
        if size !=8:
            raise NotImplementedError(f"When byte type is not None, fname is assumed, but fname was not received!")
        return self.read_fname()

    def read_int_property(self, signed=True, infered_sized = 8, from_array = False,):
        if from_array:
            value = self.read_int(infered_sized, signed=signed)
            return value
        size = self.read_int(8)
        if size != infered_sized:
            print(f"Warning: Int Size was {size} but name indicated a size of {infered_sized}")
        _ = self.file_handle.read(1)
        value = self.read_int(size, signed=signed) # When unsigned most of the time it's a bitmap
        return value

    def read_float_property(self):
        size = self.read_int(8)
        _ = self.file_handle.read(1)
        value = self.read_float(size)
        return value

    def read_enum_property(self, from_array = False):
        if from_array:
            return self.read_fname()
        enum_class_id = self.read_int(8)
        enum_class = self.read_fname()
        enum_value_id = self.read_int(1)
        enum_value = self.read_fname()

        enum_dict = {enum_class_id: enum_class, enum_value_id: enum_value}
        if len(enum_dict) < 2:
            raise Exception(f"Error: Both enum class and enum value had the same type!")

        ret_dict = {}
        for enum_type, enum_val in enum_dict.items():
            enum_key = self.SUPPORTED_ENUMS.get(enum_type)
            if enum_key is None:
                print(f"Warning: Unsupported enum key type {enum_type}")
            ret_dict[enum_key] = enum_val

        return ret_dict

        ret_dict = {}
        # 8 means class. 0 means enum value. 16 means type? 31 means template?
        if enum_class_id == 8:
            ret_dict["class"] = enum_class
        elif enum_value_id == 8:
            ret_dict["class"] = enum_value
        else:
            raise ValueError(f"Couldn't detect class for Enum!")

        if enum_value_id == 0:
            ret_dict["value"] = enum_value
        elif enum_class_id == 0:
            ret_dict["value"] = enum_class
        else:
            raise ValueError(f"Couldn't detect value for Enum!")

        return ret_dict
        # return {
        #     "class": {
        #         "id": enum_class_id, # I think 8 == class and 0 == value
        #         "name": enum_class
        #     },
        #     "value": {
        #         "id": enum_value_id,
        #         "name": enum_value
        #     }
        # }

    def read_array_property(self):
        # The way I understand it, arrays hold different variables of the same type
        # therefore you declare the type in the array itself and all children no longer need size and type
        # which in turn changes the behavior of reading non atomic types. Enums lose the class and Structs lose the size and declaration... etc
        array_size = self.read_int(8)
        array_type = self.read_fname() # TODO: I don't think this and the line below are array stuff, I think they're ObjectProperty stuff, that's why each element I have to cancel out the "from_array" stuff
        _ = self.file_handle.read(1) # Maybe LARGE flag? 0 -> 4, 1 -> 8?
        cur_tell = self.file_handle.tell()
        elements_count = self.read_int(4)
        values = []
        if array_type == "StructProperty": # TODO: Needs testing - Update: Testing seems fine
            #     array_struct_name = self.read_fname() # Assert same name as previous fname
            #     array_type = self.read_fname() # Should be the same as the caller, unsure if inside loop or outside
            values = self.read_data_as_type(array_type, loop_count=elements_count, from_array=True)
        else:
            for _ in range(elements_count):
                # Read data
                value = self.read_data_as_type(array_type, from_array=True)
                values.append(value)
        tell_diff = self._tell - cur_tell
        if tell_diff != array_size:
            raise ValueError(f"Error: Array Size did not match Expected Size! Possible wrong handling of {array_type}.\nExpected: {array_size}. Got: {tell_diff}")
        return values

    def read_string_property(self, from_array = False):
        if not from_array:
            object_size = self.read_int(8)
            _ = self.read_int(1)
        size = self.read_int(4)
        string = self.read_string(size)
        return string

    def read_name_property(self, from_array = False):
        if from_array:
            return self.read_fname()
        size = self.read_int(8)
        _ = self.file_handle.read(1)
        return self.read_fname()

    def read_text_property(self):
        size = self.read_int(8)
        unk = self.read_int(2)
        unk2 = self.read_int(4)

        if unk2 == 0xFF000000:
            unk3 = self.read_int(4)
            return []

        strings = []
        for _ in range(3):
            string = self.read_string()
            strings.append(string)
        return strings

    def read_soft_object_property(self, from_array = False):
        if not from_array:
            size = self.read_int(8)
            _ = self.file_handle.read(1)
        property_path = self.read_fname()
        # property_path = [self.read_int(4), self.read_int(4)]
        property_subpath = self.read_int(4)
        return property_path

    def read_object_property(self, element_name="", from_array=False):
        if from_array:
            return self.read_obj_reference()

        object_size = self.read_int(8)
        _ = self.file_handle.read(1) # TODO: Maybe items count... idk? NO! This exists in obj prop and soft obj prop so probably flag # Padding

        object_reference_index = self.read_obj_reference()

        # print(f"{element_name}: ObjectProperty {object_reference_index}")

        if element_name == "RowStruct": # Custom elements
            object_super = self.read_fname()
            file_name = self.read_fname_class() # incorrect
            print(f"{object_super=} {file_name=}")
            root_obj_children_count = self.read_int(4)
            print("Children Nodes Count:", root_obj_children_count)

            InventoryItems = {}
            for i in range(root_obj_children_count):
                key_name = self.read_fname()
                current_dict = self.read_struct_element()
                InventoryItems[key_name] = current_dict
                print("Read object", key_name, "for a total of", len(current_dict), "elements!")
            return InventoryItems
        elif element_name == "mLootStruct":
            object_super = self.read_fname()
            k, v = self.read_property_once() # Maybe wrong? Should be class I believe
            return {k:v}
        elif element_name == "ScriptStruct":
            # TODO: This method is wrong. It's not the element_name that decides since this points to an Object with a known definition.
            # An example here is Object of type `MKFormulaDataPtr` is of name ScriptStruct but in the SDK is a subclass of `UFormulaData`
            # Therefore MKFormulaDataPtr becomes UFormulaData, but it is a subclass so it's impossible to find it by name, instead we have to
            # Search manually. So instead of supporting the `element_name` we should support the class manually since it can't be automated
            # If there's another ScriptStruct of a different type it'll not work. The reason FModel can't view this field is because it doesn't
            # know the datatype inside and can't guess the objects so it just displays empty.
            # However, ScriptStruct is useful to know since it enforces the layout: fname, ref, data.
            script_source = self.read_fname()
            script_reference = self.read_obj_reference()
            v = {}
            # range_ = 0 if script_source == "None" else 3 # Change?
            range_ = 3
            for _ in range(range_): # TODO: The reason this is an array is cuz "None" should not be read. Or maybe it should and I have a different error
                # After testing MKFormulaDataPtr with another item (Relics.uasset) I found that size was not 3 and it was 0 actually. Perhaps have to keep reading
                # until size is fulfilled or until None is encountered, which is not possible in my scenario since there was no None.
                # What I believe now is `script_source` is the one to indicate the actual data
                key, value = self.read_property_once()
                v[key] = value
            return v
        elif element_name == "mPreReqStruct":
            value = self.read_struct_inner_element()
            return value
        elif element_name == "DataTable" and False: # Removed cuz messing with other DataTables # Need to parse by name as explained above
            table_super = self.read_fname()
            table_unk1 = self.read_int(4)
            items_count = self.read_int(4)
            table = {}
            for _ in range(items_count):
                row_key = self.read_fname()
                row_name, row_value = self.read_property_once()
                table[row_key] = {row_name:row_value}
                table_unk_extra = self.read_fname()

            return table

        return object_reference_index

    class ChainDict(dict):
        def __setitem__(self, key, value):
            if key in self:
                if isinstance(self[key], list):
                    self[key].append(value)
                else:
                    super().__setitem__(key, [self[key], value])
            else:
                super().__setitem__(key, value)

    def read_struct_property(self, loop_count=1, from_array = False):
        if from_array: # TODO: NEW UNTESTED - Update: Breaks too many things, seems like struct has no from_array
            name, value = self.read_property_once(loop_count)
            # array_struct_name = self.read_fname() # Assert same name as previous fname
            # array_type = self.read_fname() # Should be the same as the caller, unsure if inside loop or outside
            # value = self.read_data_as_type(array_type, array_struct_name, loop_count)

            return value

        struct_size = self.read_int(4)
        struct_dup_id = self.read_int(4) # When the key is the same
        struct_type = self.read_fname()

        UNK_byte = self.file_handle.read(1)
        UNK_Int1 = self.read_int(8)
        UNK_Int2 = self.read_int(8)

        cur_tell = self.file_handle.tell()
        print(f"{struct_size=} {struct_type=} (#{struct_dup_id}) {UNK_byte=} {UNK_Int1=} {UNK_Int2=}")

        if struct_type not in self.SUPPORTED_STRUCTS:
            print(f"Warning: Struct Type {struct_type} is not officially supported. Undefined behavior _may_ occur.")

        loop_data = []
        for _ in range(loop_count):
            struct_data = self.read_struct_as_type(struct_type)
            loop_data.append(struct_data)

        tell_diff = self.file_handle.tell() - cur_tell
        if tell_diff != struct_size:
            raise ValueError(f"Wrong implementation of {struct_type} as sizes don't match!\nExpected {struct_size}. Got {tell_diff}")
        if loop_count == 1:
            return loop_data[0]
        return loop_data

    def read_struct_as_type(self, struct_type: str):
        if struct_type == "DateTime":
            return self.read_datetime_struct_element()
        elif struct_type == "Color":
            return self.read_color_struct_element()
        elif struct_type == "LinearColor":
            colors = []
            for _ in range(4):
                color = self.read_float(4)
                colors.append(color)
            # full_color = f"({', '.join(str(c) for c in colors)})"
            return colors
        elif struct_type == "Timespan":
            return self.read_int(8, signed=False)
        else:
            return self.read_struct_element()

    def read_struct_inner_element(self):
        return self.read_struct_element(has_super = True)

    def read_struct_element(self, has_super = False):
        value = self.ChainDict() # Maybe not chain

        is_struct_over = self.read_fname()
        while is_struct_over != "None": # For Script Struct the struct was over but there was no None
            self.file_handle.seek(-8, 1) # Undo read
            if has_super:
                script_source = self.read_fname()
                script_reference = self.read_obj_reference()
            n, v = self.read_property_once()
            # TODO: Parsing the struct items should be here and not inside ObjectProperty # WRONG! It IS inside ObjProp
            value[n] = v
            is_struct_over = self.read_fname()

        return value

    def read_datetime_struct_element(self):
        value = self.ChainDict()
        value["date"] = self.read_int(4)
        value["time"] = self.read_int(4)
        return value

    def read_color_struct_element(self):
        color = self.read_int(4)
        alpha = color >> 24
        color = color & 0xFFFFFF
        value = f"#{color:0>6x}{alpha:0>2x}"
        return value

    def read_map_property(self, from_array = False):
        # key = self.read_fname() # Key is not always fname
        map_size = self.read_int(8)
        key_type = self.read_fname()
        value_type = self.read_fname()
        _ = self.read_int(1)

        cur_tell = self.file_handle.tell()
        unk = self.read_int(4)
        elements_count = self.read_int(4)
        map_elements = {}
        for idx in range(elements_count):
            # map_key = self.read_fname()
            map_key = self.read_data_as_type(key_type, from_array=True)
            map_value = self.read_data_as_type(value_type, map_key, from_array=True) # TODO: Is `idx` needed here?
            map_elements[map_key] = map_value
            try:
                n = self.read_fname()
                if n != "None":
                    self.file_handle.seek(-8, 1)
            except Exception:
                continue
        # element_reference_id = self.read_int(4, signed=True) # Because this is object property so I should map it correctly # TODO: ObjectType neg unk is object reference index or something
        tell_diff = self.file_handle.tell() - cur_tell
        if tell_diff != map_size:
            raise ValueError(f"Error: Expected map of size {map_size} but got size {tell_diff}")
        return map_elements

    def read_fieldpath_property(self, from_array = False):
        if not from_array:
            size = self.read_int(8)
            _ = self.read_int(1)

        paths = []
        paths_count = self.read_int(4)
        for path in range(paths_count):
            path_name = self.read_fname()
            paths.append(path_name)
        path_owner_reference = self.read_obj_reference()
        print(f"FPath with owner {path_owner_reference} had {paths_count} entries!")
        return paths

    def read_data_as_type(self, value_type: str, element_name: Any = "", loop_count = 1, from_array=False): # Element_name is only here for some specific cases, since I couldnt figure it out
        int_match = self.INT_PROPERTY_RE.match(value_type)
        if value_type == "TextProperty":
            value = self.read_text_property()
        elif value_type == "EnumProperty":
            value = self.read_enum_property(from_array)
        elif value_type == "StructProperty":
            value = self.read_struct_property(loop_count, from_array)
        elif value_type == "BoolProperty":
            value = self.read_bool_property(from_array)
        elif value_type == "ByteProperty":
            value = self.read_byte_property(from_array)
        # elif "Int" in value_type and value_type.endswith("Property"):
        elif int_match:
            signed, size_ = int_match.groups()
            signed = signed != "U"
            size_ = int(size_ or 32) // 8
            value = self.read_int_property(signed=signed, infered_sized=size_, from_array=from_array)
        elif value_type == "FloatProperty":
            value = self.read_float_property()
        elif value_type == "ArrayProperty":
            value = self.read_array_property()
        elif value_type == "NameProperty":
            value = self.read_name_property(from_array)
        elif value_type == "SoftObjectProperty":
            value = self.read_soft_object_property(from_array)
        elif value_type == "ObjectProperty":
            value = self.read_object_property(element_name, from_array)
        elif value_type == "StrProperty":
            value = self.read_string_property(from_array)
        elif value_type == "MapProperty":
            value = self.read_map_property(from_array)
        elif value_type == "FieldPathProperty":
            value = self.read_fieldpath_property(from_array)
        elif value_type == "None":
            print(f"Warning! Should not be possible. Possible corrupt file detected!")
            return None
        else:
            raise NotImplementedError(f"Value {value_type} is Not Implemented!")
        return value
