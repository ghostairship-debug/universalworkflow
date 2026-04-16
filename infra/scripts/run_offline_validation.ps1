param(
  [string]$ReportPath = "state/offline_validation_report.json",
  [int]$ApiPort = 8011,
  [switch]$SkipOfflineProbe
)

$argsList = @(
  "-m", "infra.scripts.offline_validation",
  "--report-path", $ReportPath,
  "--api-port", $ApiPort
)

if ($SkipOfflineProbe) {
  $argsList += "--skip-offline-probe"
}

python @argsList
