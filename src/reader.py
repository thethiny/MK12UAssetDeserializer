from io import BufferedReader
import struct
from typing import List, Optional

INT_PACK_DICT = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}
FLOAT_PACK_DICT = {4: 'f', 8: 'd'}

class UAssetSerializer:
    
    SUPPORTED_CLASSES = {
        "RowStruct",
        "mLootStruct"
    }
    SUPPORTED_STRUCTS = {
        "ColorPaletteSwatch",
        "MKInventoryItemPrice",
        "MKInventoryDataTableRowHandle",
        "MKInventoryItemDefinitionGroupWithAsset",
        "MKLootTable",
        "MKLootTableDropItem",
        "MKLootDropItemPicker",
        "MKLootDropItemPrerequisitePicker",
        "MK12InventoryLootItem"
    }
    
    def __init__(self, nametable: List[str] = [], reader: Optional[BufferedReader] = None):
        if nametable:
            self.set_nametable(nametable)
        if reader:
            self.file_handle = reader
            self.__init_reader()
            
    def set_nametable(self, nametable):
        self.nametable = nametable
        
    def set_reader(self, reader: BufferedReader):
        self.file_handle = reader
        self.__init_reader()
        
    def __init_reader(self):
        self.file_handle.seek(0, 2)
        self.file_size = self.file_handle.tell()
        self.file_handle.seek(0)
        
    def __bool__(self):
        return self.file_handle.tell() == self.file_size
        
    def deserialize(self,):
        return self.read_property_once()
            
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
    
    def read_property_once(self):
        element_1_name = self.read_fname()
        element_1_type = self.read_fname()
        element_1_value = self.read_data_as_type(element_1_type, element_1_name)
        return element_1_name, element_1_value
    
    # Properties
    def read_bool_property(self):
        _ = self.read_int(8)
        value = self.read_int(1)
        _ = self.file_handle.read(1)
        return value == 1

    def read_int_property(self, signed=True):
        size = self.read_int(8)
        _ = self.file_handle.read(1)
        value = self.read_int(size, signed=signed)
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
        
        ret_dict = {}
        
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
        array_size = self.read_int(8)
        array_type = self.read_fname()
        _ = self.file_handle.read(1) # Maybe LARGE flag? 0 -> 4, 1 -> 8?
        elements_count = self.read_int(4)
        values = []
        if array_type == "StructProperty": # TODO: Experimentatal Feature
            array_struct_name = self.read_fname() # Should be the same as the caller, unsure if inside loop or outside
            array_type = self.read_fname()
            values = self.read_data_as_type(array_type, loop_count=elements_count)
        else:
            for _ in range(elements_count):
                # Read data
                value = self.read_data_as_type(array_type, from_array=True)
                values.append(value)
        return values
    
    def read_string_property(self):
        array_size = self.read_int(8)
        string = self.read_string(array_size)
        _ = self.read_int(1)
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
        
    def read_object_property(self, element_name=""):
        # object_type = self.read_int(8)
        object_flags = self.read_int(4)
        object_index = self.read_int(4)
        _ = self.file_handle.read(1) # TODO: Maybe items count... idk? NO!
        
        object_unknown = self.read_int(4, signed=True)
        
        # Object uknown_try
        # object_unknown = self.nametable[object_unknown+(4-1)] # -1 due to python behavior

        print(f"{element_name}: ObjectProperty", f"{object_flags=} {object_index=} {object_unknown=}")
        
        if element_name == "RowStruct": # Custom elements
            object_super = self.read_fname()
            file_name = self.read_fname_class() # incorrect
            print(f"{object_super=} {file_name=}")
            root_obj_children_count = self.read_int(4)
            print("Children Nodes Count:", root_obj_children_count)
            
            InventoryItems = {}
            for i in range(root_obj_children_count):
                key_name = self.read_fname()
                current_dict = {}
                cur_fname = self.read_fname()
                struct_el_count = 0
                while cur_fname != "None": # NOT A CORRECT METHOD BUT A WORKING HACK!
                    self.file_handle.seek(-8, 1)
                    struct_el_count += 1
                # for _ in range(7+14): # TODO: Instead of 14, this should be a while != None since objects aren't structured, and move to ObjectProperty Handler
                    n, v = self.read_property_once()
                    current_dict[n] = v
                    cur_fname = self.read_fname()
                # _ = self.read_fname() # None
                InventoryItems[key_name] = current_dict
                print("Read object", key_name, "for a total of", struct_el_count, "elements!")
            return InventoryItems
        elif element_name == "mLootStruct":
            object_super = self.read_fname()
            return self.read_property_once()

        return None # Idk anything yet

        

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
        
        UNK_byte = self.file_handle.read(1)
        UNK_Int1 = self.read_int(8)
        UNK_Int2 = self.read_int(8)
        
        cur_tell = self.file_handle.tell()
        print(f"{struct_size=} {struct_type=} #{duplicate_id} {UNK_byte=} {UNK_Int1=} {UNK_Int2=}")
        
        loop_data = []
        for _ in range(loop_count):
            struct_data_dict = self.ChainDict()
            if struct_type == "DateTime":
                struct_data_dict["date"] = self.read_int(4)
                struct_data_dict["time"] = self.read_int(4)
            elif struct_type == "Color":
                color = self.read_int(4)
                alpha = color >> 24
                color = color & 0xFFFFFF
                value = f"#{color:0>2x}{alpha:0>2x}"
                struct_data_dict = value
            else:
                if struct_type not in self.SUPPORTED_STRUCTS:
                    print(f"Warning: Struct Type {struct_type} is not officially supported. Undefined behavior _may_ occur.")
                is_struct_over = self.read_fname() == "None"
                while is_struct_over != "None":
                    self.file_handle.seek(-8, 1) # Return from here
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                    is_struct_over = self.read_fname()
                        
            if True:
                ...
            elif struct_type == "ColorPaletteSwatch":
                for _ in range(4):
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                assert self.read_fname() == "None" # None
            elif struct_type == "MKInventoryItemPrice":
                for _ in range(3): # Either change this to be based on struct size, or change it to wait until == None
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                    
                assert self.read_fname() == "None" # None
            elif struct_type == "MKInventoryDataTableRowHandle":
                # Data Table of type ObjectProperty then RowName of type NameProperty. Probably have to hardcode instead of dyamic since objects.
                for _ in range(2):
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                
                assert self.read_fname() == "None" # None
                # TODO: If something goes bad, then uncomment the codes below,
                # and remove the check from read_name_property so that it's always True
                
                # _ = self.file_handle.read(1)
                # struct_data_dict["owner"] = self.read_fname() # None
                # struct_data_dict["extra_info_2"] = self.read_fname() # None
            elif struct_type == "MKInventoryItemDefinitionGroupWithAsset":
                for _ in range(1):
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                # _ = self.file_handle.read(1) # TODO: Most likely this is wrong and should've been in String Property
                assert self.read_fname() == "None" # None
            elif struct_type == "MKLootTable": # Should probably combine them all into while fname != None since they share the same code
                for _ in range(2):
                    n, v = self.read_property_once() # Sometimes this is only once
                    struct_data_dict[n] = v
                assert self.read_fname() == "None" # None
            elif struct_type == "MKLootTableDropItem":
                for _ in range(5): # Error in one of the loops
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                assert self.read_fname() == "None" # None
            elif struct_type == "MKLootDropItemPicker":
                for _ in range(1):
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                assert self.read_fname() == "None" # None
            elif struct_type == "MKLootDropItemPrerequisitePicker":
                # UNTESTED
                for _ in range(1):
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                assert self.read_fname() == "None" # None
            elif struct_type == "MK12InventoryLootItem":
                for _ in range(4):
                    n, v = self.read_property_once()
                    struct_data_dict[n] = v
                assert self.read_fname() == "None" # None
            else:
                raise NotImplementedError(f"Unknown StructProperty {struct_type}")

            loop_data.append(struct_data_dict)
            struct_data_dict = self.ChainDict()
        
        tell_diff = self.file_handle.tell() - cur_tell
        if tell_diff != struct_size:
            raise ValueError(f"Wrong implementation of {struct_type} as sizes don't match!\nExpected {struct_size}. Got {tell_diff}")
        if loop_count == 1:
            return loop_data[0]
        return loop_data
          
    def read_data_as_type(self, value_type: str, element_name = "", loop_count = 1, from_array=False): # Element_name is only here for some specific cases, since I couldnt figure it out
        if value_type == "TextProperty":
            value = self.read_text_property()
        elif value_type == "EnumProperty":
            value = self.read_enum_property()
        elif value_type == "StructProperty":
            value = self.read_struct_property(loop_count)
        elif value_type == "BoolProperty":
            value = self.read_bool_property()
        elif "Int" in value_type and value_type.endswith("Property"):
            signed = value_type[0] != "U"
            value = self.read_int_property(signed=signed)
        elif value_type == "FloatProperty":
            value = self.read_float_property()
        elif value_type == "ArrayProperty":
            value = self.read_array_property()
        elif value_type == "NameProperty":
            value = self.read_name_property(from_array)
        elif value_type == "SoftObjectProperty":
            value = self.read_soft_object_property()
        elif value_type == "ObjectProperty":
            value = self.read_object_property(element_name)
        elif value_type == "StrProperty":
            value = self.read_string_property()
        elif value_type == "None":
            print(f"Warning! Should not be possible. Possible corrupt file detected!")
            return None
        else:
            raise NotImplementedError(f"Value {value_type} is Not Implemented!")
        return value
    