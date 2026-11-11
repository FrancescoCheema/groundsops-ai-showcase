output "public_ip" {
  value = aws_lightsail_static_ip.staging.ip_address
}

output "instance_name" {
  value = aws_lightsail_instance.staging.name
}

output "ssh_command" {
  value = "ssh ubuntu@${aws_lightsail_static_ip.staging.ip_address}"
}
