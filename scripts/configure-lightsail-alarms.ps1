param(
    [string]$Region = "ca-central-1",
    [string]$InstanceName = "groundsops-staging",
    [Parameter(Mandatory = $true)]
    [string]$Email
)

$ErrorActionPreference = "Stop"

$contacts = aws lightsail get-contact-methods --region $Region | ConvertFrom-Json
$emailExists = $contacts.contactMethods | Where-Object {
    $_.protocol -eq "Email" -and $_.contactEndpoint -eq $Email
}
if (-not $emailExists) {
    aws lightsail create-contact-method `
        --region $Region `
        --protocol Email `
        --contact-endpoint $Email
    Write-Host "Confirm the Lightsail notification email sent to $Email."
}

$alarms = @(
    @{
        Name = "$InstanceName-status-check"
        Metric = "StatusCheckFailed"
        Operator = "GreaterThanOrEqualToThreshold"
        Threshold = "1"
        Periods = "2"
        Points = "2"
    },
    @{
        Name = "$InstanceName-high-cpu"
        Metric = "CPUUtilization"
        Operator = "GreaterThanThreshold"
        Threshold = "80"
        Periods = "3"
        Points = "3"
    },
    @{
        Name = "$InstanceName-low-burst-capacity"
        Metric = "BurstCapacityPercentage"
        Operator = "LessThanThreshold"
        Threshold = "20"
        Periods = "3"
        Points = "3"
    }
)

foreach ($alarm in $alarms) {
    aws lightsail put-alarm `
        --region $Region `
        --alarm-name $alarm.Name `
        --metric-name $alarm.Metric `
        --monitored-resource-name $InstanceName `
        --comparison-operator $alarm.Operator `
        --threshold $alarm.Threshold `
        --evaluation-periods $alarm.Periods `
        --datapoints-to-alarm $alarm.Points `
        --treat-missing-data missing `
        --contact-protocols Email `
        --notification-enabled `
        --notification-triggers ALARM OK
}

aws lightsail get-alarms `
    --region $Region `
    --monitored-resource-name $InstanceName `
    --query "alarms[].{Name:name,Metric:metricName,State:state,Threshold:threshold}" `
    --output table
