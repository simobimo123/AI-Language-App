$files = @(
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\a1.txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\a2.txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\b1txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\b2txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\c1txt',
    'c:\Users\simobimo\Documents\AI_Language_App111\ai_app_flutter_backend\backend\data\vocabulary\ar_vocavulary_to_generet\c2txt'
)

$all = foreach ($f in $files) {
    Get-Content $f | ForEach-Object {
        if ($_ -match '^\d+\.\s*(.+)') { $matches[1].Trim() }
    }
}

Write-Host "Total words: $($all.Count)" -ForegroundColor Cyan
$groups = $all | Group-Object
Write-Host "Unique words: $($groups.Count)" -ForegroundColor Cyan
$dupGroups = $groups | Where-Object Count -gt 1
Write-Host "Unique duplicate words: $($dupGroups.Count)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Distribution by count:" -ForegroundColor White
$dupGroups | Group-Object Count | Sort-Object Name -Descending | ForEach-Object {
    Write-Host "  Count $($_.Name): $($_.Count) words" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Words appearing 3 times:" -ForegroundColor Yellow
$dupGroups | Where-Object Count -eq 3 | ForEach-Object { Write-Host "  $($_.Name)" }