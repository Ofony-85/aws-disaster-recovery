output "vpc_id" {
  description = "Primary VPC ID"
  value       = aws_vpc.primary.id
}

output "ec2_instance_id" {
  description = "Primary EC2 instance ID"
  value       = aws_instance.primary_web.id
}

output "ec2_public_ip" {
  description = "Primary EC2 public IP"
  value       = aws_instance.primary_web.public_ip
}

output "rds_endpoint" {
  description = "Primary RDS endpoint"
  value       = aws_db_instance.primary.endpoint
}

output "rds_arn" {
  description = "Primary RDS ARN"
  value       = aws_db_instance.primary.arn
}

output "web_url" {
  description = "Web server URL"
  value       = "http://${aws_instance.primary_web.public_ip}"
}
