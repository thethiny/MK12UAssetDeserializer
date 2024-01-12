$outPath = "automated_all_"
mkdir $outPath 2> $NULL 1> $NULL

if (-not $args[0])
{
    Write-Output "Please pass a path";
    exit
}

$Path = $args[0]

foreach ($item in Get-ChildItem -Path $Path -Recurse -Filter *.uasset | Where-Object { $_.FullName -like "*\Inventory\*.uasset" })
{
    Copy-Item $item.fullname $outPath
}