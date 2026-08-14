<#
.SYNOPSIS
    Deploy the portfolio to Cloudflare Pages.

.DESCRIPTION
    The Cloudflare Pages project is DIRECT UPLOAD - it is not connected to
    the Git repo. Pushing to GitHub does NOT deploy the site. This script is
    the only thing that publishes changes.

    The .mp4 files in this folder are local masters. They are not referenced
    by the site (videos are YouTube embeds) and one is 160 MB, far over
    Cloudflare's 25 MiB per-file limit. So we stage only the web files into a
    temp folder and deploy that, rather than deploying the project folder.

    NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads .ps1 as
    ANSI, and non-ASCII characters break string parsing.

.PARAMETER Preview
    Deploy to a throwaway preview URL instead of production.

.EXAMPLE
    .\deploy.ps1
    Deploys to production: https://john-eldridge-portfolio.pages.dev/

.EXAMPLE
    .\deploy.ps1 -Preview
    Deploys to a preview URL, leaving the live site untouched.
#>
[CmdletBinding()]
param(
    [switch]$Preview
)

$ErrorActionPreference = 'Stop'

$ProjectName = 'john-eldridge-portfolio'
$LiveUrl     = 'https://john-eldridge-portfolio.pages.dev/'

# 'main' is the production branch. Any other branch name produces a
# preview deployment and leaves the live site unchanged.
$Branch = if ($Preview) { 'preview' } else { 'main' }

$Root = $PSScriptRoot
Push-Location $Root
try {
    # -- Stage only what the site actually needs ----------------------
    $Stage = Join-Path $env:TEMP 'portfolio-deploy'
    if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
    New-Item -ItemType Directory -Path $Stage | Out-Null

    Copy-Item -Path (Join-Path $Root 'index.html') -Destination $Stage
    Copy-Item -Path (Join-Path $Root 'styles.css') -Destination $Stage
    Copy-Item -Path (Join-Path $Root 'script.js')  -Destination $Stage
    Copy-Item -Path (Join-Path $Root '*.png')      -Destination $Stage

    $Files   = Get-ChildItem $Stage -File
    $TotalMB = [math]::Round((($Files | Measure-Object Length -Sum).Sum / 1MB), 2)
    $MaxMB   = [math]::Round((($Files | Measure-Object Length -Maximum).Maximum / 1MB), 2)

    Write-Host ""
    Write-Host "  Staged $($Files.Count) files - $TotalMB MB total, largest $MaxMB MB" -ForegroundColor Cyan

    # Cloudflare Pages rejects any single file over 25 MiB.
    $TooBig = $Files | Where-Object { $_.Length -gt 25MB }
    if ($TooBig) {
        Write-Host ""
        Write-Host "  ERROR: these files exceed Cloudflare's 25 MiB limit:" -ForegroundColor Red
        foreach ($f in $TooBig) {
            $fMB = [math]::Round($f.Length / 1MB, 2)
            Write-Host "    $($f.Name) - $fMB MB" -ForegroundColor Red
        }
        throw "Aborting: oversized files would fail the upload."
    }

    if (-not (Test-Path (Join-Path $Stage 'index.html'))) {
        throw "Aborting: index.html missing from the staged folder."
    }

    # -- Deploy ------------------------------------------------------
    Write-Host "  Deploying to '$Branch'..." -ForegroundColor Cyan
    Write-Host ""

    npx --yes wrangler@latest pages deploy $Stage --project-name=$ProjectName --branch=$Branch --commit-dirty=true

    if ($LASTEXITCODE -ne 0) { throw "wrangler exited with code $LASTEXITCODE" }

    # -- Verify (production only) ------------------------------------
    if (-not $Preview) {
        Write-Host ""
        Write-Host "  Verifying live site..." -ForegroundColor Cyan
        Start-Sleep -Seconds 3

        $bust = Get-Random

        # Compare ASCII sentinels rather than full text. Windows PowerShell
        # 5.1 reads files as ANSI and decodes responses as Latin-1, so a
        # full-text compare gives false mismatches on any non-ASCII
        # character (this page has em dashes). Sentinels sidestep that.
        $liveHtml = (Invoke-WebRequest "$LiveUrl`?cb=$bust" -UseBasicParsing).Content

        # Each entry: label, pattern, whether the pattern should be present.
        $checks = @(
            @{ Label = 'category filters'; Pattern = 'id="gallery-filters"'; Expect = $true  },
            @{ Label = 'lightbox caption'; Pattern = 'id="lightbox-caption"'; Expect = $true  },
            @{ Label = 'mobile nav';       Pattern = 'id="mobile-nav"';      Expect = $true  },
            @{ Label = 'name spelling';    Pattern = 'Eldrige';              Expect = $false },
            @{ Label = 'no old client';    Pattern = 'Remedy';               Expect = $false }
        )

        $failed = 0
        foreach ($c in $checks) {
            $found = $liveHtml -match [regex]::Escape($c.Pattern)
            if ($found -eq $c.Expect) {
                Write-Host "    OK   $($c.Label)" -ForegroundColor Green
            }
            else {
                Write-Host "    FAIL $($c.Label)" -ForegroundColor Red
                $failed++
            }
        }

        Write-Host ""
        if ($failed -eq 0) {
            Write-Host "  Live site verified." -ForegroundColor Green
        }
        else {
            Write-Host "  $failed check(s) failed. Cloudflare's edge cache can lag a few" -ForegroundColor Yellow
            Write-Host "  seconds - re-run to re-check before assuming a real problem." -ForegroundColor Yellow
        }

        Write-Host ""
        Write-Host "  $LiveUrl" -ForegroundColor Green
        Write-Host ""
    }
}
finally {
    Pop-Location
}
