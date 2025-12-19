# Primary Region Infrastructure (us-east-1)
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.primary_region
  
  default_tags {
    tags = {
      Project     = "DisasterRecovery"
      Environment = "Production"
      ManagedBy   = "Terraform"
    }
  }
}

# VPC for Primary Region
resource "aws_vpc" "primary" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "dr-primary-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "primary" {
  vpc_id = aws_vpc.primary.id

  tags = {
    Name = "dr-primary-igw"
  }
}

# Public Subnet
resource "aws_subnet" "primary_public" {
  vpc_id                  = aws_vpc.primary.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.primary_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "dr-primary-public-subnet"
  }
}

# Private Subnet 1
resource "aws_subnet" "primary_private_1" {
  vpc_id            = aws_vpc.primary.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.primary_region}a"

  tags = {
    Name = "dr-primary-private-subnet-1"
  }
}

# Private Subnet 2 (for RDS Multi-AZ)
resource "aws_subnet" "primary_private_2" {
  vpc_id            = aws_vpc.primary.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.primary_region}b"

  tags = {
    Name = "dr-primary-private-subnet-2"
  }
}

# Route Table for Public Subnet
resource "aws_route_table" "primary_public" {
  vpc_id = aws_vpc.primary.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.primary.id
  }

  tags = {
    Name = "dr-primary-public-rt"
  }
}

# Associate Route Table with Public Subnet
resource "aws_route_table_association" "primary_public" {
  subnet_id      = aws_subnet.primary_public.id
  route_table_id = aws_route_table.primary_public.id
}

# Security Group for EC2
resource "aws_security_group" "primary_web" {
  name        = "dr-primary-web-sg"
  description = "Security group for web server"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "dr-primary-web-sg"
  }
}

# Security Group for RDS
resource "aws_security_group" "primary_rds" {
  name        = "dr-primary-rds-sg"
  description = "Security group for RDS database"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.primary_web.id]
    description     = "MySQL from web servers"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "dr-primary-rds-sg"
  }
}

# EC2 Instance (Web Server)
resource "aws_instance" "primary_web" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.primary_public.id
  vpc_security_group_ids = [aws_security_group.primary_web.id]
  
  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y httpd
              systemctl start httpd
              systemctl enable httpd
              
              # Create a simple web page
              cat > /var/www/html/index.html << 'HTML'
              <!DOCTYPE html>
              <html>
              <head>
                  <title>DR Primary Server</title>
                  <style>
                      body { font-family: Arial; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
                      h1 { font-size: 3em; }
                      .info { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 600px; }
                  </style>
              </head>
              <body>
                  <h1>🌐 Disaster Recovery Demo</h1>
                  <div class="info">
                      <h2>Primary Region Server</h2>
                      <p>Region: us-east-1</p>
                      <p>Status: Active</p>
                      <p>This server has automated backups configured</p>
                  </div>
              </body>
              </html>
              HTML
              
              # Write instance metadata
              echo "Primary Web Server - $(date)" > /var/www/html/info.txt
              EOF

  tags = {
    Name   = "dr-primary-web"
    Backup = "daily"
  }
}

# Get latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "primary" {
  name       = "dr-primary-db-subnet-group"
  subnet_ids = [
    aws_subnet.primary_private_1.id,
    aws_subnet.primary_private_2.id
  ]

  tags = {
    Name = "dr-primary-db-subnet-group"
  }
}

# RDS MySQL Database
resource "aws_db_instance" "primary" {
  identifier             = "dr-primary-db"
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  
  db_name  = "disasterrecovery"
  username = var.db_username
  password = var.db_password
  
  db_subnet_group_name   = aws_db_subnet_group.primary.name
  vpc_security_group_ids = [aws_security_group.primary_rds.id]
  
  # Backup configuration
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  # Enable automated backups
  skip_final_snapshot       = false
  final_snapshot_identifier = "dr-primary-db-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  # Enable encryption
  storage_encrypted = true
  
  # Copy tags to snapshots
  copy_tags_to_snapshot = true

  tags = {
    Name   = "dr-primary-db"
    Backup = "daily"
  }
}
