param(
  [string]$ReportPath = "state/offline_validation_report.json",
  [int]$ApiPort = 8011,
  [ValidateSet("quick", "full")]
  [string]$Suite = "full",
  [string]$Shard = "",
  [double]$TimeoutSeconds = 180,
  [switch]$SkipOfflineProbe
)

$argsList = @(
  "-m", "infra.scripts.offline_validation",
  "--report-path", $ReportPath,
  "--api-port", $ApiPort,
  "--suite", $Suite,
  "--timeout-seconds", $TimeoutSeconds
)

if ($Shard) {
  $argsList += @("--shard", $Shard)
}

if ($SkipOfflineProbe) {
  $argsList += "--skip-offline-probe"
}

python @argsList
