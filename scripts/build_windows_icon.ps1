param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NativeIconMethods
{
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool DestroyIcon(IntPtr handle);
}
"@

$sizes = @(16, 20, 24, 32, 40, 48, 64, 128, 256)
$source = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $InputPath))
$images = New-Object System.Collections.Generic.List[object]

try {
    foreach ($size in $sizes) {
        $bitmap = New-Object System.Drawing.Bitmap(
            $size,
            $size,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
        )
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $stream = New-Object System.IO.MemoryStream
        $iconHandle = [IntPtr]::Zero
        $icon = $null
        try {
            $graphics.Clear([System.Drawing.Color]::Transparent)
            $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $graphics.DrawImage($source, 0, 0, $size, $size)
            $iconHandle = $bitmap.GetHicon()
            $icon = [System.Drawing.Icon]::FromHandle($iconHandle)
            $icon.Save($stream)

            $singleIcon = $stream.ToArray()
            $payloadSize = [System.BitConverter]::ToUInt32($singleIcon, 14)
            $payloadOffset = [System.BitConverter]::ToUInt32($singleIcon, 18)
            $payload = [byte[]]$singleIcon[$payloadOffset..($payloadOffset + $payloadSize - 1)]
            $planes = [System.BitConverter]::ToUInt16($payload, 12)
            $bitCount = [System.BitConverter]::ToUInt16($payload, 14)
            $colorCount = if ($bitCount -lt 8) { 1 -shl $bitCount } else { 0 }
            $images.Add([pscustomobject]@{
                Payload = $payload
                Planes = $planes
                BitCount = $bitCount
                ColorCount = $colorCount
            })
        }
        finally {
            if ($icon) {
                $icon.Dispose()
            }
            if ($iconHandle -ne [IntPtr]::Zero) {
                [NativeIconMethods]::DestroyIcon($iconHandle) | Out-Null
            }
            $stream.Dispose()
            $graphics.Dispose()
            $bitmap.Dispose()
        }
    }
}
finally {
    $source.Dispose()
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}

$file = [System.IO.File]::Create($OutputPath)
$writer = New-Object System.IO.BinaryWriter($file)
try {
    $writer.Write([uint16]0)
    $writer.Write([uint16]1)
    $writer.Write([uint16]$sizes.Count)

    $offset = 6 + (16 * $sizes.Count)
    for ($index = 0; $index -lt $sizes.Count; $index++) {
        $size = $sizes[$index]
        $image = $images[$index]
        $payload = $image.Payload
        $writer.Write([byte]$(if ($size -eq 256) { 0 } else { $size }))
        $writer.Write([byte]$(if ($size -eq 256) { 0 } else { $size }))
        $writer.Write([byte]$image.ColorCount)
        $writer.Write([byte]0)
        $writer.Write([uint16]$image.Planes)
        $writer.Write([uint16]$image.BitCount)
        $writer.Write([uint32]$payload.Length)
        $writer.Write([uint32]$offset)
        $offset += $payload.Length
    }

    foreach ($image in $images) {
        $writer.Write([byte[]]$image.Payload)
    }
}
finally {
    $writer.Dispose()
    $file.Dispose()
}
