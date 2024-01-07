Converts extracted objects from UAssets into JSON. Currently only supports InventoryDataTables and there's no plan to make it support anything else.
The root object type is determined by the file extension so each file needs its own Deserializer, however, looking at the game's code we can find that most of the game's UAssets are simply UScripts, so they share 90% of their serialization process. But since they deal with different structs and objects, everything needs to be reversed manually, therefore I see no reason for me to deserialize things that don't matter to me.

Use [MK12PMan](https://github.com/thethiny/MK12PMan) to extract UAsset into objects.