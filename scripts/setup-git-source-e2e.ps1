# Git 数据源 + 多成员团队 E2E 测试数据（仅 HTTP API，不写数据库）
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$base = "http://localhost:8000"
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function Invoke-JsonPost($uri, $obj, $headers) {
    $json = $obj | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    return Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bytes
}

function Register-User($name, $email) {
    $body = @{ username = $name; password = "test123456"; email = $email } | ConvertTo-Json
    try {
        return Invoke-RestMethod -Uri "$base/api/register" -Method POST -ContentType "application/json" -Body $body
    } catch {
        return Invoke-RestMethod -Uri "$base/api/login" -Method POST -ContentType "application/json" -Body (@{ username = $name; password = "test123456" } | ConvertTo-Json)
    }
}

function Auth-Headers($token) {
    return @{ Authorization = "Bearer $token" }
}

$ownerName = "git_ds_owner_$ts"
$adminName = "git_ds_admin_$ts"
$memberA = "git_ds_member_a_$ts"
$memberB = "git_ds_member_b_$ts"

$users = @(
    @{ name = $ownerName; email = "$ownerName@test.local"; role = "owner" }
    @{ name = $adminName; email = "$adminName@test.local"; role = "admin" }
    @{ name = $memberA; email = "$memberA@test.local"; role = "member" }
    @{ name = $memberB; email = "$memberB@test.local"; role = "member" }
)

$tokens = @{}
foreach ($u in $users) {
    Write-Host "注册/登录 $($u.name) ..."
    $r = Register-User $u.name $u.email
    $tokens[$u.name] = $r.token
}

$oh = Auth-Headers $tokens[$ownerName]
Write-Host "创建团队 ..."
$team = Invoke-JsonPost "$base/api/teams" @{ name = "Git数据源测试 $ts"; description = "E2E git source" } $oh
$teamId = $team.team_id

$invites = @{}
foreach ($u in $users) {
    if ($u.role -eq "owner") { continue }
    Write-Host "邀请 $($u.name) 为 $($u.role) ..."
    $h = Auth-Headers $tokens[$ownerName]
    $inv = Invoke-RestMethod -Uri "$base/api/teams/$teamId/invite" -Method POST -Headers $h -ContentType "application/json" -Body (@{ email = $u.email; role = $u.role } | ConvertTo-Json)
    $invites[$u.name] = $inv.token
}

foreach ($u in $users) {
    if ($u.role -eq "owner") { continue }
    Write-Host "$($u.name) 接受邀请 ..."
    $h = Auth-Headers $tokens[$u.name]
    Invoke-RestMethod -Uri "$base/api/teams/invitations/$($invites[$u.name])/accept" -Method POST -Headers $h | Out-Null
}

$out = @{
    teamId = $teamId
    teamName = $team.name
    password = "test123456"
    owner = $ownerName
    admin = $adminName
    memberA = $memberA
    memberB = $memberB
}
$out | ConvertTo-Json -Depth 3 | Set-Content -Path "$PSScriptRoot\git-source-e2e-data.json" -Encoding UTF8
Write-Host "`n已写入 scripts/git-source-e2e-data.json"
Write-Host "team_id: $teamId"
