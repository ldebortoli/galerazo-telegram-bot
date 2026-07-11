param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System;
using System.Drawing;
using System.IO;

public static class NativeIconPayload
{
    public static Rectangle FindAlphaBounds(Bitmap bitmap)
    {
        int minX = bitmap.Width;
        int minY = bitmap.Height;
        int maxX = -1;
        int maxY = -1;

        for (int y = 0; y < bitmap.Height; y++)
        {
            for (int x = 0; x < bitmap.Width; x++)
            {
                if (bitmap.GetPixel(x, y).A <= 8)
                {
                    continue;
                }
                minX = Math.Min(minX, x);
                minY = Math.Min(minY, y);
                maxX = Math.Max(maxX, x);
                maxY = Math.Max(maxY, y);
            }
        }

        if (maxX < minX || maxY < minY)
        {
            throw new InvalidOperationException("The source icon has no visible pixels.");
        }
        return Rectangle.FromLTRB(minX, minY, maxX + 1, maxY + 1);
    }

    public static byte[] Create(Bitmap bitmap)
    {
        int width = bitmap.Width;
        int height = bitmap.Height;
        int maskStride = ((width + 31) / 32) * 4;

        using (MemoryStream stream = new MemoryStream())
        using (BinaryWriter writer = new BinaryWriter(stream))
        {
            writer.Write((uint)40);
            writer.Write(width);
            writer.Write(height * 2);
            writer.Write((ushort)1);
            writer.Write((ushort)32);
            writer.Write((uint)0);
            writer.Write((uint)(width * height * 4));
            writer.Write(0);
            writer.Write(0);
            writer.Write((uint)0);
            writer.Write((uint)0);

            for (int y = height - 1; y >= 0; y--)
            {
                for (int x = 0; x < width; x++)
                {
                    Color color = bitmap.GetPixel(x, y);
                    writer.Write(color.B);
                    writer.Write(color.G);
                    writer.Write(color.R);
                    writer.Write(color.A);
                }
            }

            for (int y = height - 1; y >= 0; y--)
            {
                byte[] maskRow = new byte[maskStride];
                for (int x = 0; x < width; x++)
                {
                    if (bitmap.GetPixel(x, y).A == 0)
                    {
                        maskRow[x / 8] |= (byte)(0x80 >> (x % 8));
                    }
                }
                writer.Write(maskRow);
            }

            return stream.ToArray();
        }
    }
}
"@

$sizes = @(16, 20, 24, 32, 40, 48, 64, 128, 256)
$source = [System.Drawing.Bitmap]::FromFile((Resolve-Path -LiteralPath $InputPath))
$contentBounds = [NativeIconPayload]::FindAlphaBounds($source)
[int]$cropPadding = [Math]::Max(1, [Math]::Round($contentBounds.Width * 0.045))
[int]$compactCropSize = $contentBounds.Width + (2 * $cropPadding)
[int]$compactCropX = [Math]::Max(0, $contentBounds.X - $cropPadding)
[int]$compactCropY = [Math]::Max(0, $contentBounds.Y - [Math]::Round($cropPadding * 0.8))
[int]$compactCropSize = [Math]::Min(
    $compactCropSize,
    [Math]::Min($source.Width - $compactCropX, $source.Height - $compactCropY)
)
$compactSource = [System.Drawing.Rectangle]::new(
    $compactCropX,
    $compactCropY,
    $compactCropSize,
    $compactCropSize
)
$images = New-Object System.Collections.Generic.List[object]

try {
    foreach ($size in $sizes) {
        $bitmap = New-Object System.Drawing.Bitmap(
            $size,
            $size,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
        )
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.Clear([System.Drawing.Color]::Transparent)
            $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
            $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            if ($size -le 64) {
                [int]$targetPadding = [Math]::Max(1, [Math]::Round($size * 0.03))
                $target = [System.Drawing.Rectangle]::new(
                    $targetPadding,
                    $targetPadding,
                    $size - (2 * $targetPadding),
                    $size - (2 * $targetPadding)
                )
                $graphics.DrawImage(
                    $source,
                    $target,
                    $compactSource,
                    [System.Drawing.GraphicsUnit]::Pixel
                )
            }
            else {
                $graphics.DrawImage($source, 0, 0, $size, $size)
            }
            $images.Add([pscustomobject]@{
                Payload = [NativeIconPayload]::Create($bitmap)
                Planes = 1
                BitCount = 32
                ColorCount = 0
            })
        }
        finally {
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
