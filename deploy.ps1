<#
.SYNOPSIS
    Deploy the portfolio to Cloudflare Pages.

.DESCRIPTION
    The Cloudflare Pages project is DIRECT UPLOAD - it is not connected to
    the Git repo. Pushing to GitHub does NOT deploy the site. This script is
    the only thing that publishes changes.

    Runs audit.py first, which refuses the deploy if any page would claim
    something its files cannot support - a caption on a missing file, or a
    placement that resolves to nothing.

    Then runs build.py, which generates the deployable site into dist/:
    the legacy single-page site plus a generated page per project under
    /work/. Only dist/ is uploaded, so the .mp4 masters (one is 160 MB, far
    over Cloudflare's 25 MiB per-file limit) can never reach the CDN.

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
    # -- Audit ------------------------------------------------------
    # Checked before anything is built. A broken caption or a placement
    # pointing at nothing is a claim the files cannot support, and that
    # is worse on a live portfolio than a deploy that did not happen.
    python (Join-Path $Root 'audit.py')
    if ($LASTEXITCODE -ne 0) { throw "audit.py found errors - nothing was deployed" }

    # -- Build ------------------------------------------------------
    # build.py resizes images, enforces the 25 MiB and 20,000-file
    # ceilings, and fails non-zero rather than letting a bad upload start.
    $Stage = Join-Path $Root 'dist'

    python (Join-Path $Root 'build.py')
    if ($LASTEXITCODE -ne 0) { throw "build.py failed with code $LASTEXITCODE" }

    if (-not (Test-Path (Join-Path $Stage 'index.html'))) {
        throw "Aborting: dist/index.html missing - the build did not complete."
    }

    # -- Deploy ------------------------------------------------------
    Write-Host "  Deploying to '$Branch'..." -ForegroundColor Cyan
    Write-Host ""

    # Use the pinned wrangler from node_modules, NOT 'npx wrangler@latest'.
    # Two reasons. First, @latest re-resolves on every deploy, so a bad
    # upstream release breaks publishing with no change on our side.
    # Second, npm cannot write workerd.exe into the npx cache on this
    # machine - the extract fails with EPERM and leaves a package folder
    # with no binary in it, which produces a confusing 'installed on
    # another platform' error. Installing into node_modules avoids that
    # path entirely. Run 'npm install' if the binary is missing.
    $Wrangler = Join-Path $Root 'node_modules\.bin\wrangler.cmd'
    if (-not (Test-Path $Wrangler)) {
        throw "wrangler not found at $Wrangler - run 'npm install' first"
    }

    & $Wrangler pages deploy $Stage --project-name=$ProjectName --branch=$Branch --commit-dirty=true

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
            @{ Label = 'contact section'; Pattern = 'id="contact"';     Expect = $true  },
            @{ Label = 'back to top';     Pattern = 'id="back-to-top"'; Expect = $true  },
            @{ Label = 'mobile nav';       Pattern = 'id="mobile-nav"';      Expect = $true  },
            @{ Label = 'name spelling';    Pattern = 'Eldrige';              Expect = $false },
            @{ Label = 'no old client';    Pattern = 'Remedy';               Expect = $false },
            @{ Label = 'work section link'; Pattern = 'href="/work/"';       Expect = $true  }
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

        # The generated project index is a separate page, so check it too.
        try {
            $workHtml = (Invoke-WebRequest "$LiveUrl`work/?cb=$bust" -UseBasicParsing).Content
            if ($workHtml -match 'id="work-grid"') {
                Write-Host "    OK   /work/ project index" -ForegroundColor Green
            }
            else {
                Write-Host "    FAIL /work/ project index" -ForegroundColor Red
                $failed++
            }
        }
        catch {
            Write-Host "    FAIL /work/ did not respond" -ForegroundColor Red
            $failed++
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
