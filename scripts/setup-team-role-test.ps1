# 创建 owner / admin / member 三角色团队测试数据
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$base = "http://localhost:8000"
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function Invoke-JsonPost($uri, $obj, $headers) {
    $json = $obj | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    return Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bytes
}

function Invoke-JsonPatch($uri, $obj, $headers) {
    $json = $obj | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    return Invoke-RestMethod -Uri $uri -Method PATCH -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bytes
}

function Register-User($name, $email) {
    $body = @{ username = $name; password = "test123456"; email = $email } | ConvertTo-Json
    try {
        return Invoke-RestMethod -Uri "$base/api/register" -Method POST -ContentType "application/json" -Body $body
    } catch {
        $r = Invoke-RestMethod -Uri "$base/api/login" -Method POST -ContentType "application/json" -Body (@{ username = $name; password = "test123456" } | ConvertTo-Json)
        return $r
    }
}

function Auth-Headers($token) {
    return @{ Authorization = "Bearer $token" }
}

$ownerName = "team_owner_$ts"
$adminName = "team_admin_$ts"
$memberName = "team_member_$ts"
$ownerEmail = "$ownerName@test.local"
$adminEmail = "$adminName@test.local"
$memberEmail = "$memberName@test.local"

Write-Host "=== 注册用户 ==="
$owner = Register-User $ownerName $ownerEmail
$admin = Register-User $adminName $adminEmail
$member = Register-User $memberName $memberEmail

$oh = Auth-Headers $owner.token
$ah = Auth-Headers $admin.token
$mh = Auth-Headers $member.token

Write-Host "=== Owner 创建团队 ==="
$team = Invoke-JsonPost "$base/api/teams" @{ name = "角色测试团队 $ts"; description = "E2E" } $oh
$teamId = $team.team_id
Write-Host "team_id: $teamId"

Write-Host "=== Owner 邀请 admin / member ==="
$invAdmin = Invoke-RestMethod -Uri "$base/api/teams/$teamId/invite" -Method POST -Headers $oh -ContentType "application/json" -Body (@{ email = $adminEmail; role = "admin" } | ConvertTo-Json)
$invMember = Invoke-RestMethod -Uri "$base/api/teams/$teamId/invite" -Method POST -Headers $oh -ContentType "application/json" -Body (@{ email = $memberEmail; role = "member" } | ConvertTo-Json)

Write-Host "=== 接受邀请 ==="
$adminJoin = Invoke-RestMethod -Uri "$base/api/teams/invitations/$($invAdmin.token)/accept" -Method POST -Headers $ah
$memberJoin = Invoke-RestMethod -Uri "$base/api/teams/invitations/$($invMember.token)/accept" -Method POST -Headers $mh

Write-Host "=== 验证成员列表 ==="
$members = Invoke-RestMethod -Uri "$base/api/teams/$teamId/members" -Headers $oh
$members | ForEach-Object { Write-Host "  $($_.username): $($_.role)" }

# member 不能改团队名 (403)
Write-Host "=== 权限探测 (member PATCH team) ==="
try {
    Invoke-RestMethod -Uri "$base/api/teams/$teamId" -Method PATCH -Headers $mh -ContentType "application/json" -Body '{"name":"hack"}' -ErrorAction Stop
    Write-Host "  member PATCH team: UNEXPECTED OK"
} catch {
    Write-Host "  member PATCH team: $($_.Exception.Response.StatusCode.value__) (expected 403)"
}

# admin 可以改团队名
Write-Host "=== admin PATCH team ==="
$patched = Invoke-JsonPatch "$base/api/teams/$teamId" @{ name = "角色测试团队 $ts (admin改)" } $ah
Write-Host "  name: $($patched.name)"

# member 不能删团队
Write-Host "=== member DELETE team ==="
try {
    Invoke-WebRequest -Uri "$base/api/teams/$teamId" -Method DELETE -Headers $mh -ErrorAction Stop | Out-Null
    Write-Host "  UNEXPECTED OK"
} catch {
    Write-Host "  status: $($_.Exception.Response.StatusCode.value__) (expected 403)"
}

@{
    teamId = $teamId
    teamName = $patched.name
    owner = @{ username = $ownerName; password = "test123456" }
    admin = @{ username = $adminName; password = "test123456" }
    member = @{ username = $memberName; password = "test123456" }
} | ConvertTo-Json -Depth 3 | Set-Content -Path "$PSScriptRoot\team-role-test-data.json" -Encoding UTF8

Write-Host "`n已写入 scripts/team-role-test-data.json"
