$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"

function Resolve-Node {
  $systemNode = Get-Command node -ErrorAction SilentlyContinue
  if ($systemNode) {
    return $systemNode.Source
  }

  if (Test-Path $bundledNode) {
    return $bundledNode
  }

  throw "Node.js was not found. Install Node.js from https://nodejs.org/ or run this from Codex where the bundled runtime exists."
}

$node = Resolve-Node
Set-Location $projectRoot
& $node --test
