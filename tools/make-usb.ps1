<#
.SYNOPSIS
  Assemble the unlock USB from the built image.

.DESCRIPTION
  Copies the contents of `src/USB/` (EFI + pinned firmware assets) to a FAT32 USB
  drive, or a staging directory. Prints the EFI SHA-256 so you can record it.

.EXAMPLE
  .\tools\make-usb.ps1 -Drive E:
  .\tools\make-usb.ps1 -OutDir C:\staging
#>
[CmdletBinding()]
param(
    [string]$Drive,
    [string]$OutDir,
    [switch]$SkipFSCheck
)
$ErrorActionPreference = 'Stop'
$src = Join-Path $PSScriptRoot '..\src\USB'
if (-not (Test-Path -LiteralPath $src)) {
    throw "Source USB tree not found: $src. Run 'python build.py' first."
}

if ($OutDir) {
    $dst = $OutDir.TrimEnd('\') + '\'
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
}
elseif ($Drive) {
    $letter = ($Drive -replace '[^A-Za-z]', '').ToUpper()
    $dst = $letter + ':\'
    if (-not (Test-Path -LiteralPath $dst)) { throw "Drive not found: $dst" }
    if (-not $SkipFSCheck) {
        $fs = (Get-Volume -DriveLetter $letter -ErrorAction SilentlyContinue).FileSystem
        if ($fs -and $fs -ne 'FAT32') {
            Write-Warning "Filesystem is '$fs', not FAT32. UEFI may not boot this drive."
        }
    }
}
else { throw "Provide -Drive (e.g. E:) or -OutDir." }

Write-Host "Copying USB tree -> $dst ..."
Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force

$efi = Join-Path $dst 'EFI\BOOT\BOOTX64.EFI'
if (-not (Test-Path -LiteralPath $efi)) { throw "EFI missing after copy: $efi" }

$assets = Join-Path $dst 'RTX4080-EXPERIMENT\ASSETS'
$required = 'booter_load_ad102.bin','v67-ad102-610.43.03-four-plm.bin','gsp_ga10x.bin','gsp_boot_ad102.bin','gsp_boot_desc_ad102.bin'
foreach ($a in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $assets $a))) { throw "Missing asset: $a" }
}

$hash = (Get-FileHash -LiteralPath $efi -Algorithm SHA256).Hash
Write-Host "USB ready. EFI SHA-256: $hash"
Write-Host "Next: fully power off, boot this USB, wait for READY, press U once (per card)."
