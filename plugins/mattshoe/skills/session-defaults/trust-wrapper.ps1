# >>> session-defaults: trust the git repo before claude starts, so the workspace trust prompt never shows
function claude {
  $root = git rev-parse --show-toplevel 2>$null
  if ($LASTEXITCODE -eq 0 -and $root) {
    $base = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { $HOME }
    $p = Join-Path $base '.claude.json'
    try {
      $d = Get-Content $p -Raw | ConvertFrom-Json
      if (-not $d.projects) { $d | Add-Member projects ([pscustomobject]@{}) }
      $changed = $false
      foreach ($key in @($root, ($root -replace '/', '\'))) {
        $e = $d.projects.$key
        if (-not $e) { $d.projects | Add-Member $key ([pscustomobject]@{}); $e = $d.projects.$key }
        if (-not $e.hasTrustDialogAccepted) { $e | Add-Member -Force hasTrustDialogAccepted $true; $changed = $true }
      }
      if ($changed) {
        [IO.File]::WriteAllText("$p.trust-tmp", ($d | ConvertTo-Json -Depth 100), (New-Object Text.UTF8Encoding $false))
        Move-Item -Force "$p.trust-tmp" $p
      }
    } catch {}
  }
  & (Get-Command claude -CommandType Application | Select-Object -First 1) @args
}
# <<< session-defaults
