#!/usr/bin/env pwsh

# =================================================================
# TELEGRAM FOOTBALL COACH BOT - DEVELOPMENT TEST RESET
# =================================================================
# Simple reset script for testing during development
# Run with: .\test_reset.ps1

Write-Host "🧪 DEVELOPMENT TEST RESET" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# Backup current data
$backupDir = "dev_backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

if (Test-Path "bot_data.json") {
    Copy-Item "bot_data.json" $backupDir
    Write-Host "✅ Backed up bot_data.json" -ForegroundColor Green
}

if (Test-Path "questionnaire_data.json") {
    Copy-Item "questionnaire_data.json" $backupDir
    Write-Host "✅ Backed up questionnaire_data.json" -ForegroundColor Green
}

if (Test-Path "admins.json") {
    Copy-Item "admins.json" $backupDir
    Write-Host "✅ Backed up admins.json" -ForegroundColor Green
}

# Reset data files
@"
{
    "users": {},
    "course_selections": {},
    "payment_receipts": {},
    "payments": {},
    "questionnaire_progress": {},
    "admin_notifications": []
}
"@ | Out-File -FilePath "bot_data.json" -Encoding UTF8

@"
{
    "responses": {},
    "photos": {},
    "completed": []
}
"@ | Out-File -FilePath "questionnaire_data.json" -Encoding UTF8

@"
{
    "admins": [],
    "last_sync": null
}
"@ | Out-File -FilePath "admins.json" -Encoding UTF8

# Clear directories
if (Test-Path "user_documents") {
    Remove-Item "user_documents\*" -Recurse -Force
    Write-Host "✅ Cleared user documents" -ForegroundColor Green
}

if (Test-Path "questionnaire_photos") {
    Remove-Item "questionnaire_photos\*" -Recurse -Force
    Write-Host "✅ Cleared questionnaire photos" -ForegroundColor Green
}

if (Test-Path "exports") {
    Remove-Item "exports\*" -Recurse -Force
    Write-Host "✅ Cleared exports" -ForegroundColor Green
}

Write-Host "`n🎉 Development test reset complete!" -ForegroundColor Green
Write-Host "📂 Backup saved to: $backupDir" -ForegroundColor Yellow
Write-Host "🚀 Ready for fresh testing!" -ForegroundColor Cyan
