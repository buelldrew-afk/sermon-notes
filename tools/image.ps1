# Crop (optional) and shrink one photo to a phone-friendly JPEG.
# Crop values are fractions of the image (0.1 = 10%), as PowerPoint stores them.
param(
  [Parameter(Mandatory)] [string]$In,
  [Parameter(Mandatory)] [string]$Out,
  [int]$MaxSide = 1600,
  [double]$CropL = 0, [double]$CropT = 0, [double]$CropR = 0, [double]$CropB = 0,
  [int]$Quality = 82,
  [int]$Rotate = 0   # degrees clockwise, as set in PowerPoint (90, 180, 270)
)
Add-Type -AssemblyName System.Drawing
$src = [System.Drawing.Image]::FromFile((Resolve-Path $In))
try {
  # Phone photos store rotation in EXIF; turn the pixels upright first.
  if ($src.PropertyIdList -contains 0x0112) {
    $o = [int]$src.GetPropertyItem(0x0112).Value[0]
    $flip = @{ 2 = 'RotateNoneFlipX'; 3 = 'Rotate180FlipNone'; 4 = 'Rotate180FlipX'; 5 = 'Rotate90FlipX'; 6 = 'Rotate90FlipNone'; 7 = 'Rotate270FlipX'; 8 = 'Rotate270FlipNone' }[$o]
    if ($flip) { $src.RotateFlip([System.Drawing.RotateFlipType]::$flip) }
  }
  $x =[int]($src.Width * $CropL); $y = [int]($src.Height * $CropT)
  $w = [int]($src.Width * (1 - $CropL - $CropR)); $h = [int]($src.Height * (1 - $CropT - $CropB))
  $scale = [math]::Min(1.0, $MaxSide / [math]::Max($w, $h))
  $nw = [int]($w * $scale); $nh = [int]($h * $scale)
  $bmp = New-Object System.Drawing.Bitmap $nw, $nh
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.DrawImage($src, (New-Object System.Drawing.Rectangle 0, 0, $nw, $nh), (New-Object System.Drawing.Rectangle $x, $y, $w, $h), [System.Drawing.GraphicsUnit]::Pixel)
  $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
  $ep = New-Object System.Drawing.Imaging.EncoderParameters 1
  $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), ([long]$Quality)
  $g.Dispose()
  $r = @{ 90 = 'Rotate90FlipNone'; 180 = 'Rotate180FlipNone'; 270 = 'Rotate270FlipNone' }[(($Rotate % 360) + 360) % 360]
  if ($r) { $bmp.RotateFlip([System.Drawing.RotateFlipType]::$r) }
  $bmp.Save($Out, $codec, $ep)
  $bmp.Dispose()
} finally { $src.Dispose() }
