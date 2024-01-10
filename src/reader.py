from io import BufferedReader
import struct
from typing import List, Optional

from numpy import array_split

INT_PACK_DICT = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}
FLOAT_PACK_DICT = {4: 'f', 8: 'd'}

class UAssetSerializer:
    def __init__(self, nametable: List[str] = [], reader: Optional[BufferedReader] = None):
        if nametable:
            self.set_nametable(nametable)
        if reader:
            self.file_handle = reader
            
    def set_nametable(self, nametable):
        self.nametable = nametable
        
    def set_reader(self, reader: BufferedReader):
        self.file_handle = reader
            
    # Reads   
    def read_fname(self,):
        name = self.read_int(4, endianness="le", signed=False)
        name_suffix = self.read_int(4, endianness="le", signed=False)
        name = self.nametable[name]
        if name_suffix:
            # Noticed that all items start at 2 instead of 0, so BG_Ashrah.2 is actually BG_Ashrah_1
            name += f"_{name_suffix-1}" # Enable if you want
            # name += f".{name_suffix}" # Enable if you want
        return name

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
        string_size = size if size is not None else self.read_int(4)
        string = self.file_handle.read(string_size).decode()
        ret_str = ''
        for s in string:
            if s == '\x00':
                break
            ret_str += s
        return ret_str
    
    def read_struct_property_item(self):
        element_1_name = self.read_fname()
        element_1_type = self.read_fname()
        element_1_value = self.read_data_as_type(element_1_type)
        return element_1_name, element_1_value
    
    # Properties
    def read_bool_property(self):
        _ = self.read_int(8)
        _ = self.file_handle.read(1)
        return self.read_int(1)

    def read_int_property(self):
        size = self.read_int(8)
        _ = self.file_handle.read(1)
        value = self.read_int(size)    
        return value

    def read_float_property(self):
        size = self.read_int(8)
        _ = self.file_handle.read(1)
        value = self.read_float(size)
        return value
    
    def read_enum_property(self):
        enum_class_id = self.read_int(8)
        enum_class = self.read_fname()
        enum_value_id = self.read_int(1)
        enum_value = self.read_fname()
        return {
            "class": {
                "id": enum_class_id,
                "name": enum_class
            },
            "value": {
                "id": enum_value_id,
                "name": enum_value
            }
        }
    
    def read_array_property(self):
        array_size = self.read_int(8)
        array_type = self.read_fname()
        _ = self.file_handle.read(1) # Maybe LARGE flag? 0 -> 4, 1 -> 8?
        elements_count = self.read_int(4)
        values = []
        if array_type == "StructProperty": # TODO: Experimentation Feature
            array_struct_name = self.read_fname() # Should be the same as the caller, unsure if inside loop or outside
            array_type = self.read_fname()
            values = self.read_data_as_type(array_type, elements_count)
        else:
            for _ in range(elements_count):
                # Read data
                value = self.read_data_as_type(array_type, from_array=True)
                values.append(value)
        return values
    
    def read_string_property(self):
        array_size = self.read_int(8)
        string = self.read_string(array_size)
        return string
    
    def read_name_property(self, from_array = False):
        if from_array:
            return self.read_fname()
        size = self.read_int(8)
        _ = self.file_handle.read(1)
        return self.read_fname()
 
    def read_text_property(self):
        size = self.read_int(8)
        _ = self.file_handle.read(1)
        unk = self.read_int(4)
        flags = self.read_int(4)
        if flags == 255: # I believe 255 is -1
            strings_count = 0
            _ = self.file_handle.read(1)
        elif flags == 256:
            strings_count = 2
            _ = self.file_handle.read(2)
        else:
            raise NotImplementedError(f"Unknown Text Property {flags}")
        # flag_log = int(math.log(flags, 256)) + 1 # They're 8 byte flags + unk amt of padding
        # _ = f.read(flag_log) # Padding or something idk
        strings = []
        for _ in range(strings_count):
            string = self.read_string()
            strings.append(string)
        return strings
        
    def read_soft_object_property(self):
        size = self.read_int(8)
        _ = self.file_handle.read(1)
        property_path = self.read_fname()
        # property_path = [self.read_int(4), self.read_int(4)]
        property_type = self.read_int(4)
        return property_path
        
    def read_object_property(self):
        # object_type = self.read_int(8)
        object_flags = self.read_int(4)
        object_index = self.read_int(4)
        _ = self.file_handle.read(1) # TODO: Maybe items count... idk? NO!
        object_unknown = self.read_int(4, signed=True)
        
        print("Object Property:", f"{object_flags=} {object_index=} {object_unknown=}")
        # data_dict = {}
        return None # Idk anything yet
        # if object_type == 4: # Also wrong probably
            # return None
        #     row_key = read_fname(f)
        #     row_type = read_fname(f)
        #     row_value = read_data_as_type(f, row_type)
        #     data_dict[row_key] = row_value
        # else:
        #     raise NotImplementedError(f"Unknown Object {object_type}")
        

    class ChainDict(dict):
        def __setitem__(self, key, value):
            if key in self:
                if isinstance(self[key], list):
                    self[key].append(value)
                else:
                    super().__setitem__(key, [self[key], value])
            else:
                super().__setitem__(key, value)
        
    def read_struct_property(self, loop_count=1):
        struct_size = self.read_int(4)
        duplicate_id = self.read_int(4)
        struct_type = self.read_fname()
        # struct_data_dict = self.ChainDict()
        UNK_byte = self.file_handle.read(1)
        UNK_Int1 = self.read_int(8)
        UNK_Int2 = self.read_int(8)
        cur_tell = self.file_handle.tell()
        print("We are currently in")
        print(f"{struct_size=} {struct_type=} #{duplicate_id} {UNK_byte=} {UNK_Int1=} {UNK_Int2=}")
        print("Current Tell", cur_tell)
        loop_data = []
        for loop in range(loop_count):
            struct_data_dict = self.ChainDict()
            if struct_type == "DateTime":
                struct_data_dict["date"] = self.read_int(4)
                struct_data_dict["time"] = self.read_int(4)
                # _ = f.read(17) # Uknown
            elif struct_type == "MKInventoryItemPrice":
                for _ in range(3):
                    n, v = self.read_struct_property_item()
                    struct_data_dict[n] = v
                    
                assert self.read_fname() == "None" # None
            elif struct_type == "MKInventoryDataTableRowHandle":
                # Data Table of type ObjectProperty then RowName of type NameProperty. Probably have to hardcode instead of dyamic since objects.
                for _ in range(2):
                    n, v = self.read_struct_property_item()
                    struct_data_dict[n] = v
                
                assert self.read_fname() == "None" # None
                # TODO: If something goes bad, then uncomment the codes below,
                # and remove the check from read_name_property so that it's always True
                
                # _ = self.file_handle.read(1)
                # struct_data_dict["owner"] = self.read_fname() # None
                # struct_data_dict["extra_info_2"] = self.read_fname() # None
            elif struct_type == "MKInventoryItemDefinitionGroupWithAsset":
                for _ in range(1):
                    n, v = self.read_struct_property_item()
                    struct_data_dict[n] = v
                _ = self.file_handle.read(1)
                assert self.read_fname() == "None" # None
            elif struct_type == "ColorPaletteSwatch":
                for _ in range(4):
                    n, v = self.read_struct_property_item()
                    struct_data_dict[n] = v
                assert self.read_fname() == "None" # None
            elif struct_type == "Color":
                color = self.read_int(4)
                alpha = color >> 24
                color = color & 0xFFFFFF
                value = f"#{color:0>2x}{alpha:0>2x}"
                struct_data_dict = value
            else:
                raise NotImplementedError(f"Unknown StructProperty {struct_type}")

            loop_data.append(struct_data_dict)
            struct_data_dict = self.ChainDict()
        
        # new_tell = self.file_handle.tell()
        # print(f"Tell: {cur_tell} -> {new_tell} = {new_tell-cur_tell}")
        
        tell_diff = self.file_handle.tell() - cur_tell
        if tell_diff != struct_size:
            raise ValueError(f"Wrong implementation of {struct_type} as sizes don't match!\nExpected {struct_size}. Got {tell_diff}")
        if loop_count == 1:
            return loop_data[0]
        return loop_data
          
    def read_data_as_type(self, value_type, loop_count = 1, from_array=False):
        if value_type == "TextProperty":
            value = self.read_text_property()
        elif value_type == "EnumProperty":
            value = self.read_enum_property()
        elif value_type == "StructProperty":
            value = self.read_struct_property(loop_count)
        elif value_type == "BoolProperty":
            value = self.read_bool_property()
        elif value_type == "IntProperty":
            value = self.read_int_property()
        elif value_type == "FloatProperty":
            value = self.read_float_property()
        elif value_type == "ArrayProperty":
            value = self.read_array_property()
        elif value_type == "NameProperty":
            value = self.read_name_property(from_array)
        elif value_type == "SoftObjectProperty":
            value = self.read_soft_object_property()
        elif value_type == "ObjectProperty":
            value = self.read_object_property()
        elif value_type == "StrProperty":
            value = self.read_string_property()
        else:
            raise NotImplementedError(f"Value {value_type} is Not Implemented!")
        return value
    