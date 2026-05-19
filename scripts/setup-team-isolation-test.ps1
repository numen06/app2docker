# Team isolation test (ASCII labels only — avoids PS5 GBK script parsing mojibake)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$base = "http://localhost:8000"
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$pass = "test123456"

function Invoke-JsonPost($uri, $obj, $headers) {
    $json = $obj | ConvertTo-Json -Compress -Depth 6
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $resp = Invoke-WebRequest -Uri $uri -Method POST -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bytes -UseBasicParsing
    return $resp.Content | ConvertFrom-Json
}

function Register-User($name, $email) {
    $bodyObj = @{ username = $name; password = $pass; email = $email }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($bodyObj | ConvertTo-Json -Compress))
    try {
        $resp = Invoke-WebRequest -Uri "$base/api/register" -Method POST -ContentType "application/json; charset=utf-8" -Body $bytes -UseBasicParsing
        return $resp.Content | ConvertFrom-Json
    } catch {
        $loginBytes = [System.Text.Encoding]::UTF8.GetBytes((@{ username = $name; password = $pass } | ConvertTo-Json -Compress))
        $resp = Invoke-WebRequest -Uri "$base/api/login" -Method POST -ContentType "application/json; charset=utf-8" -Body $loginBytes -UseBasicParsing
        return $resp.Content | ConvertFrom-Json
    }
}

function Write-Utf8JsonFile($path, $obj) {
    $json = $obj | ConvertTo-Json -Depth 6
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, $json, $utf8)
}

function Auth-Headers($token) {
    return @{ Authorization = "Bearer $token" }
}

function Get-Pipelines($headers, $teamId) {
    $uri = "$base/api/pipelines"
    if ($teamId) { $uri += "?team_id=$teamId" }
    $r = Invoke-RestMethod -Uri $uri -Headers $headers
    return @($r.pipelines)
}

function Get-GitSources($headers, $teamId) {
    $uri = "$base/api/git-sources"
    if ($teamId) { $uri += "?team_id=$teamId" }
    $r = Invoke-RestMethod -Uri $uri -Headers $headers
    return @($r.sources)
}

function Assert-Names($label, $items, $nameField, $expectInclude, $expectExclude) {
    $names = @($items | ForEach-Object { $_.$nameField })
    $ok = $true
    foreach ($inc in $expectInclude) {
        if ($names -notcontains $inc) {
            Write-Host "  [FAIL] $label : 缺少 $inc (实际: $($names -join ', '))" -ForegroundColor Red
            $ok = $false
        }
    }
    foreach ($exc in $expectExclude) {
        if ($names -contains $exc) {
            Write-Host "  [FAIL] $label : 不应包含 $exc (实际: $($names -join ', '))" -ForegroundColor Red
            $ok = $false
        }
    }
    if ($ok) {
        Write-Host "  [PASS] $label : $($names -join ', ')" -ForegroundColor Green
    }
    return $ok
}

$userA = "iso_user_a_$ts"
$userB = "iso_user_b_$ts"
$emailA = "$userA@test.local"
$emailB = "$userB@test.local"

Write-Host "=== 注册两个独立用户 ===" -ForegroundColor Cyan
$authA = Register-User $userA $emailA
$authB = Register-User $userB $emailB
$hA = Auth-Headers $authA.token
$hB = Auth-Headers $authB.token

Write-Host "=== create teams ===" -ForegroundColor Cyan
$teamNameA = "Team-Isolation-A-$ts"
$teamNameB = "Team-Isolation-B-$ts"
$teamA = Invoke-JsonPost "$base/api/teams" @{ name = $teamNameA; description = "isolation test A" } $hA
$teamB = Invoke-JsonPost "$base/api/teams" @{ name = $teamNameB; description = "isolation test B" } $hB
$teamIdA = $teamA.team_id
$teamIdB = $teamB.team_id
Write-Host "  TeamA: $teamIdA"
Write-Host "  TeamB: $teamIdB"

$pipeNameA = "ISO-PIPE-A-$ts"
$pipeNameB = "ISO-PIPE-B-$ts"
$srcNameA = "ISO-SRC-A-$ts"
$srcNameB = "ISO-SRC-B-$ts"

Write-Host "=== 各团队创建 Git 数据源 ===" -ForegroundColor Cyan
$srcA = Invoke-JsonPost "$base/api/git-sources" @{
    team_id = $teamIdA
    name = $srcNameA
    git_url = "https://gitee.com/example/repo-a.git"
    description = "team A only"
} $hA
$srcB = Invoke-JsonPost "$base/api/git-sources" @{
    team_id = $teamIdB
    name = $srcNameB
    git_url = "https://gitee.com/example/repo-b.git"
    description = "team B only"
} $hB

Write-Host "=== 各团队创建流水线 ===" -ForegroundColor Cyan
$pipeA = Invoke-JsonPost "$base/api/pipelines" @{
    team_id = $teamIdA
    name = $pipeNameA
    git_url = "https://gitee.com/example/app-a.git"
    image_name = "iso-a"
    description = "team A pipeline"
} $hA
$pipeB = Invoke-JsonPost "$base/api/pipelines" @{
    team_id = $teamIdB
    name = $pipeNameB
    git_url = "https://gitee.com/example/app-b.git"
    image_name = "iso-b"
    description = "team B pipeline"
} $hB
$pipeIdA = $pipeA.pipeline_id
$pipeIdB = $pipeB.pipeline_id

$allPass = $true

Write-Host "`n=== 用户 A 列表隔离（带 team_id）===" -ForegroundColor Cyan
$pA_onA = Get-Pipelines $hA $teamIdA
$pA_onB = Get-Pipelines $hA $teamIdB
$sA_onA = Get-GitSources $hA $teamIdA
$sA_onB = Get-GitSources $hA $teamIdB

$allPass = (Assert-Names "A 查流水线 team=A" $pA_onA "name" @($pipeNameA) @($pipeNameB)) -and $allPass
$allPass = (Assert-Names "A 查流水线 team=B" $pA_onB "name" @() @($pipeNameA, $pipeNameB)) -and $allPass
$allPass = (Assert-Names "A 查数据源 team=A" $sA_onA "name" @($srcNameA) @($srcNameB)) -and $allPass
$allPass = (Assert-Names "A 查数据源 team=B" $sA_onB "name" @() @($srcNameA, $srcNameB)) -and $allPass

Write-Host "`n=== 用户 B 列表隔离（带 team_id）===" -ForegroundColor Cyan
$pB_onB = Get-Pipelines $hB $teamIdB
$pB_onA = Get-Pipelines $hB $teamIdA
$sB_onB = Get-GitSources $hB $teamIdB
$sB_onA = Get-GitSources $hB $teamIdA

$allPass = (Assert-Names "B 查流水线 team=B" $pB_onB "name" @($pipeNameB) @($pipeNameA)) -and $allPass
$allPass = (Assert-Names "B 查流水线 team=A" $pB_onA "name" @() @($pipeNameA, $pipeNameB)) -and $allPass
$allPass = (Assert-Names "B 查数据源 team=B" $sB_onB "name" @($srcNameB) @($srcNameA)) -and $allPass
$allPass = (Assert-Names "B 查数据源 team=A" $sB_onA "name" @() @($srcNameA, $srcNameB)) -and $allPass

Write-Host "`n=== cross-team GET by id (expect 403/404) ===" -ForegroundColor Cyan
$cases = @(
    @{ label = "A get B pipeline"; headers = $hA; uri = "$base/api/pipelines/$pipeIdB" },
    @{ label = "B get A pipeline"; headers = $hB; uri = "$base/api/pipelines/$pipeIdA" },
    @{ label = "A get B source"; headers = $hA; uri = "$base/api/git-sources/$($srcB.source_id)" },
    @{ label = "B get A source"; headers = $hB; uri = "$base/api/git-sources/$($srcA.source_id)" }
)
foreach ($case in $cases) {
    try {
        Invoke-RestMethod -Uri $case.uri -Headers $case.headers -ErrorAction Stop | Out-Null
        Write-Host "  [FAIL] $($case.label) : 意外成功" -ForegroundColor Red
        $allPass = $false
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -in 403, 404) {
            Write-Host "  [PASS] $($case.label) : HTTP $code" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $($case.label) : HTTP $code" -ForegroundColor Red
            $allPass = $false
        }
    }
}

Write-Host "`n=== cross-team create (expect 403) ===" -ForegroundColor Cyan
try {
    Invoke-JsonPost "$base/api/pipelines" @{
        team_id = $teamIdB
        name = "HACK-PIPE-$ts"
        git_url = "https://gitee.com/example/hack.git"
    } $hA
    Write-Host "  [FAIL] A create pipeline on team B: unexpected OK" -ForegroundColor Red
    $allPass = $false
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 403) {
        Write-Host "  [PASS] A create pipeline on team B: HTTP 403" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] A create pipeline on team B: HTTP $code" -ForegroundColor Red
        $allPass = $false
    }
}

$out = @{
    timestamp = $ts
    teamA = @{ id = $teamIdA; name = $teamNameA; pipeline = $pipeNameA; source = $srcNameA }
    teamB = @{ id = $teamIdB; name = $teamNameB; pipeline = $pipeNameB; source = $srcNameB }
    userA = @{ username = $userA; password = $pass }
    userB = @{ username = $userB; password = $pass }
    allPass = $allPass
}
Write-Utf8JsonFile "$PSScriptRoot\team-isolation-test-data.json" $out

Write-Host "`nWrote scripts/team-isolation-test-data.json (UTF-8)" -ForegroundColor Cyan
if ($allPass) {
    Write-Host "=== isolation tests PASSED ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== isolation tests FAILED ===" -ForegroundColor Red
    exit 1
}
