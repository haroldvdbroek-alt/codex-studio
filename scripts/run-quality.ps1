#requires -Version 5.1
<#
.SYNOPSIS
Voer alleen-lezen quality uit en bewaar een nieuw JSON-rapport.
.DESCRIPTION
Maakt GEEN Windows-taak. Start geen tests, installaties, back-up of herstel.
PythonPath en ReportDirectory moeten expliciete, bestaande lokale paden zijn.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$PythonPath = '',
    [string]$ReportDirectory = ''
)

Set-StrictMode -Version Latest

function Resolve-CheckedLocalPath {
    param(
        [string]$Value,
        [ValidateSet('File', 'Directory')][string]$Kind
    )
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -notmatch '^[A-Za-z]:[\\/]') {
        throw 'Gebruik een volledig lokaal schijfpad.'
    }
    if ($Value.Substring(2).Contains(':') -or $Value.IndexOfAny([char[]]'"<>|?*') -ge 0) {
        throw 'Datastromen, devicepaden en onveilige padtekens zijn niet toegestaan.'
    }
    foreach ($character in $Value.ToCharArray()) {
        if ([char]::IsControl($character) -or [char]::GetUnicodeCategory($character) -eq 'Format') {
            throw 'Stuurtekens in paden zijn niet toegestaan.'
        }
    }
    $fullPath = [System.IO.Path]::GetFullPath($Value)
    $drive = [System.IO.DriveInfo]::new([System.IO.Path]::GetPathRoot($fullPath))
    if ($drive.DriveType.ToString() -notin @('Fixed', 'Removable', 'Ram')) {
        throw 'Gebruik geen netwerkschijf of onbekend schijftype.'
    }
    $item = Get-Item -LiteralPath $fullPath -Force -ErrorAction Stop
    if ($item.PSProvider.Name -ne 'FileSystem') {
        throw 'Alleen bestandssysteempaden zijn toegestaan.'
    }
    if (($Kind -eq 'File' -and $item.PSIsContainer) -or ($Kind -eq 'Directory' -and -not $item.PSIsContainer)) {
        throw 'Pad heeft niet het gevraagde bestandstype.'
    }
    $ancestor = $item
    while ($null -ne $ancestor) {
        if (($ancestor.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Symlinks en junctions zijn niet toegestaan.'
        }
        if ($ancestor -is [System.IO.FileInfo]) {
            $ancestor = $ancestor.Directory
        }
        else {
            $ancestor = $ancestor.Parent
        }
    }
    return $item.FullName
}

$checkStage = 'instellingen'
try {
    if ($env:OS -ne 'Windows_NT') {
        throw 'Dit script is bedoeld voor Windows.'
    }
    $checkStage = 'PythonPath'
    $checkedPython = Resolve-CheckedLocalPath -Value $PythonPath -Kind File
    if ([System.IO.Path]::GetFileName($checkedPython) -notmatch '^python(?:[0-9]+(?:\.[0-9]+)*)?\.exe$') {
        throw 'Gebruik de echte Python-console-interpreter, geen alias of pythonw.exe.'
    }
    $checkStage = 'ReportDirectory'
    $checkedReports = Resolve-CheckedLocalPath -Value $ReportDirectory -Kind Directory
    $checkStage = 'studiomap'
    $null = Resolve-CheckedLocalPath -Value $PSCommandPath -Kind File
    $studioDirectory = Resolve-CheckedLocalPath -Value ([System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))) -Kind Directory
    $studioFile = Resolve-CheckedLocalPath -Value (Join-Path $studioDirectory 'studio.py') -Kind File
    $timestamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ', [Globalization.CultureInfo]::InvariantCulture)
    $identifier = [Guid]::NewGuid().ToString('N')
    $reportPath = Join-Path $checkedReports ("quality-{0}-{1}.json" -f $timestamp, $identifier)
    # Vaste argumenten, geen commandotekst opbouwen en geen doorgegeven $args.
    # -E negeert PYTHON*-omgevingsvariabelen; -S voorkomt site/startuphooks.
    # De vertrouwde scriptmap blijft beschikbaar voor eigen studio-imports.
    $qualityArguments = @('-E', '-S', '-B', $studioFile, 'quality', '--format', 'json', '--output', $reportPath)
    $checkStage = 'quality uitvoeren'
    Push-Location -LiteralPath $studioDirectory -ErrorAction Stop
    try {
        & $checkedPython @qualityArguments
        $qualityExitCode = [int]$LASTEXITCODE
    }
    finally {
        Pop-Location -ErrorAction Stop
    }
    if ($qualityExitCode -in @(0, 1)) {
        $checkStage = 'opgeslagen rapport controleren'
        $checkedReport = Resolve-CheckedLocalPath -Value $reportPath -Kind File
        $reportItem = Get-Item -LiteralPath $checkedReport -Force -ErrorAction Stop
        if ($reportItem.Length -gt (4 * 1024 * 1024)) {
            throw 'Rapport overschrijdt de limiet.'
        }
        $report = Get-Content -LiteralPath $checkedReport -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
        if ($report.schema_version -ne 1 -or $report.command -cne 'quality' -or
            $report.tests_requested -isnot [bool] -or $report.tests_requested -ne $false -or
            $report.exit_code -ne $qualityExitCode) {
            throw 'Rapport bevestigt niet de verwachte alleen-lezen controle.'
        }
    }
    # Bewaar de quality-exitcode, ook als de controle FAIL oplevert.
    exit $qualityExitCode
}
catch {
    [Console]::Error.WriteLine(('Quality-script mislukt bij {0}. Controleer de lokale paden, Python 3.11+, toegangsrechten en het rapport. Geen taak aangemaakt.' -f $checkStage))
    exit 3
}
