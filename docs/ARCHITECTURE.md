# AWS Disaster Recovery System Architecture

## System Overview

This disaster recovery system provides automated backup and recovery capabilities across two AWS regions with comprehensive monitoring and testing.

## Architecture Diagram
```
PRIMARY REGION (us-east-1)              SECONDARY REGION (us-west-2)
┌─────────────────────────┐            ┌─────────────────────────┐
│  VPC (10.0.0.0/16)     │            │  VPC (10.1.0.0/16)     │
│  ├── Public Subnet     │            │  ├── Public Subnet     │
│  ├── Private Subnet    │            │  ├── Private Subnet    │
│                         │            │                         │
│  EC2 Web Server        │──────────► │  AMI Backup            │
│  (Auto AMI Daily)      │  Copy      │  (Cross-Region)        │
│                         │            │                         │
│  RDS MySQL             │──────────► │  RDS Snapshot          │
│  (Automated Backup)    │  Replicate │  (Cross-Region)        │
│                         │            │                         │
│  S3 Bucket (Data)      │──────────► │  S3 Replica            │
│  (Versioning On)       │  CRR       │  (Cross-Region)        │
│                         │            │                         │
│  Lambda Monitor        │            │  Lambda Restore Test   │
│  (Check Backups)       │            │  (Weekly Verification) │
│                         │            │                         │
│  CloudWatch            │            │  CloudWatch            │
│  (Metrics/Logs)        │            │  (Metrics/Logs)        │
└─────────────────────────┘            └─────────────────────────┘
```

## Components

### 1. EC2 Web Server
- **Type:** t2.micro
- **OS:** Amazon Linux 2
- **Purpose:** Web application hosting
- **Backup:** Daily AMI via DLM
- **RTO:** 30-60 minutes

### 2. RDS MySQL Database
- **Type:** db.t3.micro
- **Engine:** MySQL 8.0
- **Purpose:** Application database
- **Backup:** Automated hourly snapshots
- **RPO:** 1 hour
- **RTO:** 2-3 hours

### 3. S3 Storage
- **Purpose:** Application data storage
- **Features:** Versioning, encryption, lifecycle policies
- **Backup:** Cross-region replication
- **RPO:** 15 minutes
- **RTO:** 15 minutes

### 4. Monitoring System
- **Components:** Lambda functions, CloudWatch, SNS
- **Frequency:** Continuous (every 6 hours)
- **Alerts:** Email via SNS
- **Dashboard:** CloudWatch custom dashboard

### 5. Automated Testing
- **RDS Tests:** Weekly (Sundays 2 AM UTC)
- **EC2 Tests:** Weekly (Sundays 3 AM UTC)
- **Cleanup:** Daily (midnight UTC)
- **Validation:** Automated post-test

## Security

### Encryption
- **S3:** AES-256 server-side encryption
- **RDS:** Encryption at rest enabled
- **Snapshots:** Encrypted
- **AMIs:** Encrypted EBS volumes

### Access Control
- **IAM Roles:** Least privilege principle
- **Security Groups:** Restricted ingress
- **VPC:** Private subnets for databases

## Costs

### Monthly Estimate
- **EC2:** ~$8-10 (t2.micro)
- **RDS:** ~$15-20 (db.t3.micro)
- **S3:** ~$1-2 (with lifecycle)
- **Snapshots:** ~$5-8
- **Data Transfer:** ~$2-5
- **Lambda:** ~$0.50-1
- **Total:** ~$32-46/month

---

**Version:** 1.0  
**Date:** $(date)
