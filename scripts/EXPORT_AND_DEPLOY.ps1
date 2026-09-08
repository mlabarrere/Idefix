# Script PowerShell pour exporter les données et déployer sur Vercel
# À exécuter sur ta machine Windows locale

# 1. Activer le venv Python
Write-Host "==> Activating Python venv..." -ForegroundColor Cyan
.\.venv\Scripts\Activate.ps1

# 2. Vérifier DATABASE_URL
Write-Host "`n==> Checking DATABASE_URL..." -ForegroundColor Cyan
if (-not $env:DATABASE_URL) {
    # Charger .env si pas déjà set
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            Set-Item -Path "env:$($Matches[1])" -Value $Matches[2]
        }
    }
}
Write-Host "DATABASE_URL: $($env:DATABASE_URL.Substring(0, 50))..." -ForegroundColor Green

# 3. Export mission russosphere
Write-Host "`n==> Exporting russosphere data..." -ForegroundColor Cyan
$env:PYTHONPATH = "."
python scripts/export_static.py --mission russosphere

# 4. Export mission gan
Write-Host "`n==> Exporting gan data..." -ForegroundColor Cyan
python scripts/export_static.py --mission gan

# 5. Vérifier que les données existent
Write-Host "`n==> Verifying exported data..." -ForegroundColor Cyan
$russosphereData = Get-ChildItem -Path webapp/public/data/russosphere -ErrorAction SilentlyContinue
$ganData = Get-ChildItem -Path webapp/public/data/gan -ErrorAction SilentlyContinue

if ($russosphereData) {
    Write-Host "✓ russosphere: $($russosphereData.Count) files" -ForegroundColor Green
} else {
    Write-Host "✗ russosphere: NO DATA" -ForegroundColor Red
}

if ($ganData) {
    Write-Host "✓ gan: $($ganData.Count) files" -ForegroundColor Green
} else {
    Write-Host "✗ gan: NO DATA" -ForegroundColor Red
}

# 6. Commit et push
Write-Host "`n==> Committing data bundle..." -ForegroundColor Cyan
git add webapp/public/data/
git status --short
$commitMsg = @"
feat: add static data bundle (russosphere + gan)

Generated from Supabase PostgreSQL via export_static.py.
Bundle includes: channels.json, graph.json, episodes/, snapshots/.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
"@
git commit -m $commitMsg
git push

# 7. Redeploy sur Vercel (optionnel - auto-deploy via GitHub)
Write-Host "`n==> Deploy to Vercel..." -ForegroundColor Cyan
Write-Host "Vercel auto-deploys from GitHub push." -ForegroundColor Yellow
Write-Host "OU manuellement: cd webapp && vercel --prod" -ForegroundColor Yellow

Write-Host "`n==> DONE! Check https://webapp-rho-sooty-24.vercel.app in ~2 min" -ForegroundColor Green
