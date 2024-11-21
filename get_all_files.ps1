$outPath = "automate_auto"
mkdir $outPath 2> $NULL 1> $NULL

if (-not $args[0])
{
    Write-Output "Please pass a path";
    exit
}

if ($args[1]) # if you pass a 2nd arg then it's inventory
{
    Write-Output "Inventories Only"
    $likePath = "*\Inventory\*.uasset"
} else
{
    $likePath = "*\*.uasset"
}

$Path = $args[0]

foreach ($item in Get-ChildItem -Path $Path -Recurse -Filter *.uasset | Where-Object { $_.FullName -like $likePath })
{
    Copy-Item $item.fullname $outPath
    Write-Output $item.fullname
}