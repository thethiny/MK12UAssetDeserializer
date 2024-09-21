import os
import struct as structdata
from typing import List, Tuple, TypeVar, overload
import uuid

from test.pythoninfo import dump_info

_T = TypeVar("_T")


class Struct:
    SIZE_FORMATS = {
        1: "B",
        2: "H",
        4: "I",
        8: "Q",
    }

    def __init__(self, file_handle):
        self.file_handle = file_handle

    @classmethod
    def parametrize_struct(cls, class_, param_dict):
        for k, v in param_dict.items():
            setattr(class_, k, v)

    @classmethod
    def unpack(cls, struct, data):
        struct_format = "".join(
            [f"{cls.SIZE_FORMATS.get(size, f'{size}s')}" for _, size in struct]
        )
        unpacked_data = structdata.unpack(struct_format, data)
        params = {name: value for (name, _), value in zip(struct, unpacked_data)}
        return params

    @classmethod
    def read(cls, write_class: _T, struct, file_handle) -> _T:
        if not isinstance(struct, list):
            raise ValueError("Struct was not a struct!")

        data = file_handle.read(Struct.get_struct_size(struct))
        cls.parametrize_struct(write_class, cls.unpack(struct, data))
        return write_class

    @classmethod
    def read_raw(cls, struct, file_handle):
        struct_format = "".join(
            [f"{cls.SIZE_FORMATS.get(size, f'{size}s')}" for size in struct]
        )
        data = file_handle.read(sum(struct))
        return structdata.unpack(struct_format, data)

    @classmethod
    def get_struct_size(cls, struct):
        return sum([s[1] for s in struct])


class StructSpawn(Struct):
    params = {}

    def read(self):
        return super().read(self, self.params, self.file_handle)  # To allow chaining

    def print(self):
        print(self)
        return self

    def __str__(self):
        s = ""
        for name, _ in self.params:
            v = getattr(self, name)
            try:
                v = f"{v} (0x{v:2>0X})"
            except Exception:
                pass
            s += f"{name}: {v}\n"
            
        return s

    def __repr__(self):
        return str(self)
    
    def param(self, p):
        return getattr(self, p)
    
    def __getitem__(self, p):
        return self.param(p)


class UAssetHeader(StructSpawn):
    params = [
        (
            "FilePathFName",
            8,
        ),
        ("EngineFilesCount", 8),
        ("UFlags", 4),
        ("DataLocationInUCas", 4),
        ("NameTableOffset", 4),
        ("NameTableSize", 4),
        ("ImportDataOffset", 4),
        ("ImportDataSize", 4),
        ("Table0Location", 4),
        ("ExportsLocation", 4),
        ("Table2Location", 4),
        ("ImportTableOffset", 4),
        ("ImportTableSize", 8),
    ]


class ExportTableEntry(StructSpawn):
    params = [
        ("ObjectLocation", 8),
        ("ObjectSize", 8),
        ("ObjectName", 8),
        ("UNK1", 8),
        ("UNK2", 8),
        ("UNK3", 8),
        ("ObjectClassSignature", 16),
        ("ObjectClass", 8),
    ]

    def __str__(self, name_table: List[str]):
        offset = self["ObjectLocation"]
        size = self["ObjectSize"]
        
        _name = self["ObjectName"]
        name = name_table[_name]
        class_ = self["ObjectClass"]
        
        unk1 = self["UNK1"]
        unk2 = self["UNK2"]
        unk3 = self["UNK3"]
        
        guid = self["ObjectClassSignature"]
        
        guid = str(uuid.UUID(bytes=guid)).upper()

        s = f"{offset:X} ({size:X}): {name} ({class_:X}) [{unk1:X} | {unk2:X} | {unk3:X}] [{guid}]"
        return s

class ImportTableEntry(StructSpawn):
    params = [
        ("UnknownHash", 8),
        ("NameIndex", 8),
        ("UNK", 4),
    ]
    
    def __str__(self, name_table: List[str]):
        hash_ = self["UnknownHash"]
        name = name_table[self["NameIndex"]]
        unk = self["UNK"]
        
        s = f"Import {hash_:0>16X} for Object {name} with {unk=:X}"
        return s


class FName:
    def __init__(self, length, string):
        self.length = length
        self.string = string


class UAsset:
    def __init__(self, f, dump_raw: bool = False, dump_parsed: bool = False, dump_folder: str = ""):
        if isinstance(f, str):
            self.file_name = os.path.basename(f)  # Get only the file name from the full path
            f = open(f, "rb")
        else:
            self.file_name = os.path.basename(f.name)  # Get only the file name from the open file object

        self.file_handle = f
        self.dump_raw_flag = dump_raw
        self.dump_parsed_flag = dump_parsed
        if (self.dump_raw or self.dump_parsed) and not dump_folder:
            print(f"Defaulting dump folder to `extracted` since value was empty")
            dump_folder = "extracted"
        self.dump_folder = dump_folder

    def get_dump_location(self, *path):
        dump = os.path.join(self.dump_folder, self.file_name, *path)
        os.makedirs(os.path.dirname(dump), exist_ok=True)
        return dump

    def dump_raw(self, obj, *path, extension=".uAsset"):
        path = self.get_dump_location("Raw", *path)
        path += extension
        with open(path, "wb") as f:
            return f.write(obj)

    def dump_parsed(self, obj, *path, enum="hex", extension=".txt"):
        path = self.get_dump_location("Parsed", *path)
        path += extension
        if enum in [None, ""]:
            format = "{v}"
        elif enum == "int":
            format = "{i:d}: {v}"
        else:
            format = "{i:0>2X}: {v}"

        with open(path, "w") as f:
            if not hasattr(obj, "__iter__"):
                obj = str(obj).split("\n")
            i = 0
            for i, line in enumerate(obj):
                try:
                    line = line.__str__(self.name_table) # type: ignore
                except Exception:
                    line = str(line)
                line = format.format(i=i, v=line)
                f.write(line + "\n")
        return i

    def get_header(self, header):
        return getattr(self.header, header)

    def init_uasset(self):
        self.header = UAssetHeader(self.file_handle).read()

        self.name_table = list(self.read_name_table())

        self.file_handle.seek(self.get_header("ImportDataOffset"))
        self.import_data = self.file_handle.read(self.get_header("ImportDataSize"))

        self.table0 = self.file_handle.read(
            self.get_header("ExportsLocation") - self.get_header("Table0Location")
        )
        self.export_table = list(self.read_exports_table())
        self.table2 = self.file_handle.read(
            self.get_header("ImportTableOffset") - self.get_header("Table2Location")
        )
        self.import_table = list(self.read_imports_table())
        # self.import_table = self.file_handle.read(self.get_header("ImportTableSize"))

        if self.dump_raw_flag:
            self.dump_raw(self.import_data, "ImportData")
            self.dump_raw(self.table0, "Table0")
            self.dump_raw(self.table2, "Table2")

        if self.dump_parsed_flag:
            self.dump_parsed(self.header, "Header", enum="")
            self.dump_parsed(self.name_table, "NameTable")
            self.dump_parsed(self.export_table, "ExportTable")
            self.dump_parsed(self.import_table, "ImportTable")

        return self # For Chaining

    @property
    def exports(self):
        yield from self.read_exports()

    def read_name_table(self):
        cur_tell = self.file_handle.tell()
        while self.file_handle.tell() - cur_tell < self.get_header("NameTableSize"):
            name_size = self.read([2])[0]
            name_size = int.from_bytes(
                name_size.to_bytes(2, byteorder="little"), byteorder="big" # type: ignore
            )
            name = self.read(name_size).decode("utf-8")
            yield name
        if self.dump_raw_flag:
            done_tell = self.file_handle.tell()
            self.file_handle.seek(cur_tell)
            self.dump_raw(self.file_handle.read(done_tell-cur_tell), "NameTable")

    def read_exports_table(self):
        size = self.get_header("Table2Location") - self.get_header("ExportsLocation")
        cur_tell = self.file_handle.tell()
        while self.file_handle.tell() - cur_tell < size:
            yield ExportTableEntry(self.file_handle).read()
        if self.dump_raw_flag:
            done_tell = self.file_handle.tell()
            self.file_handle.seek(cur_tell)
            self.dump_raw(self.file_handle.read(done_tell-cur_tell), "ExportTable")

    def read_imports_table(self):
        size = self.header["ImportTableSize"]
        loc = self.header["ImportTableOffset"]
        imports_count = int.from_bytes(self.read(4), "little")
        for _ in range(imports_count):
            yield ImportTableEntry(self.file_handle).read()
        assert self.file_handle.tell() - loc == size # Make sure I read correctly
        
        if self.dump_raw_flag:
            self.file_handle.seek(loc)
            self.dump_raw(self.file_handle.read(size), "ImportTable")

    def read_exports(self):
        for i, export in enumerate(self.export_table):
            size: int = export.ObjectSize  # type: ignore
            # file_location: int = export.ObjectLocation - self.get_header("DataLocationInUCas") # type: ignore

            file_name = f"{i}_{self.fname_to_name(export.ObjectName)}_{export.ObjectClass:x}"  # type: ignore

            data = self.read(size)
            if self.dump_raw_flag:
                self.dump_raw(data, "Exports", file_name, extension="")
            yield file_name, data

    def read_struct(self, struct):
        if not isinstance(struct[0], (list, tuple)):
            return Struct.read_raw(struct, self.file_handle)
        return Struct.read(self, struct, self.file_handle)

    @overload
    def read(self, size: list, *args, **kwargs) -> Tuple[bytes]: ...

    @overload
    def read(self, size: int, *args, **kwargs) -> bytes: ...

    def read(self, size, *args, **kwargs):
        if isinstance(size, list):  # Assumes a struct info
            return self.read_struct(size)
        return self.file_handle.read(size, *args, **kwargs)

    def fname_to_name(self, fname):
        return self.name_table[fname]


if __name__ == "__main__":
    try:
        # f = "services/MK12UAssetExtractor/src/SubZero_Fatalities.uasset"
        f = ""
        d = UAsset(f).init_uasset()
    except FileNotFoundError:
        # f = "SubZero_Fatalities.uasset"
        # f = "Announcer_SeasonOfSoulEater.uasset"
        f = "MavadoKAM_Kameo.uasset"
        d = UAsset(f).init_uasset()
    print(dict(d.exports))
