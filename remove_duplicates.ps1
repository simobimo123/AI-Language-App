# Script to remove duplicate words across all vocabulary files
# Keeps only the first occurrence of each word

$sourceDir = 'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet'
$backupDir = Join-Path $sourceDir 'backup_before_dedup'
$files = @('a1.txt', 'a2.txt', 'b1txt', 'b2txt', 'c1txt', 'c2txt')

# Step 1: Create backup
Write-Host "Creating backup..." -ForegroundColor Yellow
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}
foreach ($f in $files) {
    $src = Join-Path $sourceDir $f
    $dst = Join-Path $backupDir $f
    Copy-Item $src $dst -Force
}
Write-Host "Backup created in: $backupDir" -ForegroundColor Green

# Step 2: Read all words in order
Write-Host "Reading all files..." -ForegroundColor Yellow
$allEntries = @()  # Array of [PSCustomObject]@{Word; File; OriginalLine}
foreach ($f in $files) {
    $path = Join-Path $sourceDir $f
    $lineNum = 0
    Get-Content $path | ForEach-Object {
        $lineNum++
        if ($_ -match '^\d+\.\s*(.+)') {
            $allEntries += [PSCustomObject]@{
                Word = $matches[1].Trim()
                File = $f
                OriginalLine = $_
                OriginalLineNum = $lineNum
            }
        }
    }
}

Write-Host "Total words found: $($allEntries.Count)" -ForegroundColor Cyan

# Step 3: Deduplicate
Write-Host "Deduplicating..." -ForegroundColor Yellow
$seen = @{}
$keptEntries = @()
$dupCount = 0
foreach ($entry in $allEntries) {
    $w = $entry.Word
    if (-not $seen.ContainsKey($w)) {
        $seen[$w] = $true
        $keptEntries += $entry
    } else {
        $dupCount++
    }
}

Write-Host "Removed $dupCount duplicate entries" -ForegroundColor Yellow
Write-Host "Kept $($keptEntries.Count) unique words" -ForegroundColor Green

# Step 4: Group by file and write back
Write-Host "Writing deduplicated files..." -ForegroundColor Yellow
$byFile = $keptEntries | Group-Object File
foreach ($group in $byFile) {
    $fname = $group.Name
    $path = Join-Path $sourceDir $fname
    $lines = @()
    $i = 1
    foreach ($entry in $group.Group) {
        $lines += "$i. $($entry.Word)"
        $i++
    }
    Set-Content -Path $path -Value $lines -Encoding UTF8
    Write-Host "  Wrote $($lines.Count) words to $fname" -ForegroundColor Gray
}

Write-Host "`nDone! All files deduplicated." -ForegroundColor Green