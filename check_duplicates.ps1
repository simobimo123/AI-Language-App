$files = @(
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\a1.txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\a2.txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\b1txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\b2txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\c1txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\c2txt'
)

$allWords = @()
foreach ($file in $files) {
    $lines = Get-Content $file
    foreach ($line in $lines) {
        if ($line -match '^\d+\.\s*(.+)') {
            $word = $matches[1].Trim()
            $allWords += [PSCustomObject]@{
                Word = $word
                File = [System.IO.Path]::GetFileName($file)
                Line = $line
            }
        }
    }
}

Write-Host "إجمالي الكلمات: $($allWords.Count)" -ForegroundColor Cyan
$uniqueCount = ($allWords | Group-Object Word | Where-Object Count -eq 1).Count
$dupes = $allWords | Group-Object Word | Where-Object Count -gt 1
Write-Host "الكلمات الفريدة: $uniqueCount" -ForegroundColor Cyan
Write-Host "Total duplicate instances: $((($allWords | Group-Object Word | Where-Object Count -gt 1).Count))" -ForegroundColor Cyan
Write-Host "Total unique duplicate words: $($dupes.Count)" -ForegroundColor Yellow
Write-Host ""
Write-Host "الكلمات المكررة (التي تظهر أكثر من مرة):" -ForegroundColor Yellow
$dupes | Sort-Object Count -Descending | ForEach-Object {
    $occurrences = $_.Group | ForEach-Object { "$($_.File): $($_.Line)" }
    Write-Host "  $($_.Name) - تكرر $($_.Count) مرات:" -ForegroundColor White
    $occurrences | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
}