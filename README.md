# AWS Disaster Recovery & Backup Automation System

A production-ready disaster recovery system with automated backups, cross-region replication, and restore testing for EC2, RDS, and S3.

## 🌟 Features

- ✅ Automated RDS snapshot backups with cross-region replication
- ✅ EC2 AMI management with Data Lifecycle Manager (DLM)
- ✅ S3 cross-region replication with versioning
- ✅ Comprehensive monitoring with CloudWatch
- ✅ Automated weekly restore testing
- ✅ SNS email alerts for all backup operations
- ✅ CloudWatch dashboard for visual monitoring
- ✅ Automated cleanup of test resources

## 📊 Metrics

- **RTO (Recovery Time Objective):** 2-4 hours
- **RPO (Recovery Point Objective):** 1 hour
- **Backup Retention:** 7 days
- **Cost:** ~$32-46/month
- **Regions:** us-east-1 (primary), us-west-2 (DR)

## 🏗️ Architecture

### Primary Region (us-east-1)
- EC2 t2.micro web server
- RDS MySQL db.t3.micro
- S3 bucket with versioning

### DR Region (us-west-2)
- AMI copies (7-day retention)
- RDS snapshot copies (7-day retention)
- S3 replica bucket

### Monitoring
- Lambda functions for health checks
- CloudWatch dashboard
- SNS email notifications

## 🚀 Quick Start

### Prerequisites
- AWS Account with credits
- AWS CLI configured
- Python 3.9+
- Terraform 1.0+
- Git

## 📋 Components

### 1. RDS Backups
- **Frequency:** Hourly automated snapshots
- **Retention:** 7 days in both regions
- **Cross-Region:** Automated daily copy to us-west-2
- **Testing:** Weekly restore validation

### 2. EC2 AMI Backups
- **Frequency:** Daily at 3:00 AM UTC
- **Retention:** 7 AMIs in both regions
- **Method:** AWS Data Lifecycle Manager (DLM)
- **Cross-Region:** Automated copy
- **Testing:** Weekly launch validation

### 3. S3 Replication
- **Method:** Cross-Region Replication (CRR)
- **Latency:** ~15 minutes
- **Features:** Versioning, encryption, lifecycle policies
- **Testing:** Continuous validation

### 4. Monitoring & Alerts
- **Health Checks:** Every 6 hours
- **Daily Summary:** 8:00 AM UTC
- **Alarms:** RDS age, S3 replication, backup health
- **Notifications:** SNS email alerts

### 5. Automated Testing
- **RDS Restore:** Sundays 2:00 AM UTC
- **EC2 Restore:** Sundays 3:00 AM UTC
- **Cleanup:** Daily midnight UTC
- **Results:** Email notifications

## 📖 Documentation

- [Disaster Recovery Runbook](docs/DISASTER_RECOVERY_RUNBOOK.md)
- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Cost Analysis](docs/COST_ANALYSIS.md)

## 🧪 Testing

### Manual Tests
```bash
# Test RDS restore
./scripts/test-rds-restore.sh

# Test EC2 restore
./scripts/test-ec2-restore.sh
```

## 📊 Monitoring

### CloudWatch Dashboard
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=DR-Backup-Monitoring

### Key Metrics
- RDS snapshot count and age
- S3 replication lag
- AMI count by region
- Backup health score

## 💰 Cost Analysis

### Monthly Costs (Estimated)
| Service | Cost |
|---------|------|
| EC2 (t2.micro) | $8-10 |
| RDS (db.t3.micro) | $15-20 |
| S3 Storage | $1-2 |
| Snapshots | $5-8 |
| Data Transfer | $2-5 |
| Lambda | $0.50-1 |
| **Total** | **$32-46** |

## 🧹 Teardown

To delete all resources:
```bash
./scripts/teardown-all.sh
```

**Warning:** This will delete all backups and cannot be undone!

## 📝 Project Structure
```
aws-disaster-recovery/
├── terraform/primary/          # Primary region infrastructure
├── lambda/                     # Lambda functions
│   ├── master-backup-monitor/
│   ├── rds-restore-tester/
│   ├── ec2-restore-tester/
│   └── test-cleanup/
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
└── README.md
```

## 👤 Author

**Ofonime Offong**
- GitHub: [@Ofony-85](https://github.com/Ofony-85)

---

**Created:** $(date)  
**Status:** Production Ready  
**Version:** 1.0
