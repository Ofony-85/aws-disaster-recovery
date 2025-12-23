# Disaster Recovery Runbook

## Table of Contents
1. [Overview](#overview)
2. [RTO & RPO](#rto--rpo)
3. [Emergency Contacts](#emergency-contacts)
4. [Disaster Scenarios](#disaster-scenarios)
5. [Recovery Procedures](#recovery-procedures)
6. [Verification Steps](#verification-steps)

---

## Overview

This runbook provides step-by-step procedures to recover from various disaster scenarios affecting the primary region (us-east-1).

**Primary Region:** us-east-1 (N. Virginia)  
**DR Region:** us-west-2 (Oregon)  

**Backup Assets:**
- RDS MySQL Database (automated snapshots + cross-region copies)
- S3 Bucket Data (cross-region replication)
- EC2 AMIs (DLM-managed + cross-region copies)

---

## RTO & RPO

**Recovery Time Objective (RTO):** 2-4 hours  
**Recovery Point Objective (RPO):** 1 hour  

| Service | RTO | RPO | Notes |
|---------|-----|-----|-------|
| RDS Database | 2-3 hours | 1 hour | Automated snapshots every hour |
| EC2 Instances | 30-60 minutes | 24 hours | Daily AMI backups |
| S3 Data | 15 minutes | 15 minutes | Real-time replication |

---

## Emergency Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Primary On-Call | [Your Name] | your-email@example.com | +XXX-XXX-XXXX |
| AWS Support | AWS | - | Support Console |

---

## Disaster Scenarios

### Scenario 1: Primary Region Outage
**Impact:** Complete loss of us-east-1  
**Recovery:** Activate DR region (us-west-2)  

### Scenario 2: RDS Database Failure
**Impact:** Database unavailable  
**Recovery:** Restore from latest snapshot  

### Scenario 3: EC2 Instance Failure
**Impact:** Web server unavailable  
**Recovery:** Launch from latest AMI  

### Scenario 4: Data Corruption
**Impact:** S3 data corrupted  
**Recovery:** Restore from DR bucket or previous version  

---

## Recovery Procedures

### Full Region Failover

**When to Use:** Complete us-east-1 outage

**Prerequisites:**
- Verify us-east-1 is truly unavailable
- Obtain authorization from leadership
- Alert all stakeholders

**Steps:**

#### 1. Verify Backups in DR Region
```bash
# Check RDS snapshots
aws rds describe-db-snapshots --region us-west-2

# Check AMIs
aws ec2 describe-images --owners self --region us-west-2

# Check S3 replication
aws s3 ls s3://[DR-BUCKET-NAME] --region us-west-2
```

#### 2. Restore RDS Database
```bash
# Get latest snapshot
SNAPSHOT_ID=$(aws rds describe-db-snapshots \
    --region us-west-2 \
    --query 'DBSnapshots[-1].DBSnapshotIdentifier' \
    --output text)

# Restore database
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier dr-failover-db \
    --db-snapshot-identifier $SNAPSHOT_ID \
    --db-instance-class db.t3.micro \
    --region us-west-2

# Wait for availability (10-15 minutes)
aws rds wait db-instance-available \
    --db-instance-identifier dr-failover-db \
    --region us-west-2
```

#### 3. Launch EC2 Instances
```bash
# Get latest AMI
AMI_ID=$(aws ec2 describe-images \
    --owners self \
    --region us-west-2 \
    --query 'Images[-1].ImageId' \
    --output text)

# Get default VPC subnet
SUBNET_ID=$(aws ec2 describe-subnets \
    --region us-west-2 \
    --filters "Name=default-for-az,Values=true" \
    --query 'Subnets[0].SubnetId' \
    --output text)

# Create security group
SG_ID=$(aws ec2 create-security-group \
    --group-name dr-failover-sg \
    --description "DR Failover Security Group" \
    --region us-west-2 \
    --query 'GroupId' \
    --output text)

# Add rules
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region us-west-2

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region us-west-2

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type t2.micro \
    --subnet-id $SUBNET_ID \
    --security-group-ids $SG_ID \
    --region us-west-2 \
    --query 'Instances[0].InstanceId' \
    --output text)

# Wait for running state
aws ec2 wait instance-running \
    --instance-ids $INSTANCE_ID \
    --region us-west-2

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region us-west-2 \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "Instance launched at: http://$PUBLIC_IP"
```

#### 4. Verify Application
```bash
# Test web server
curl http://$PUBLIC_IP

# Test database connection
# Update application with new DB endpoint
```

**Estimated Time:** 2-3 hours  

---

## Verification Steps

After any recovery procedure:

### 1. Application Health Check
```bash
curl -I http://[SERVER-IP]
# Expected: HTTP 200 OK
```

### 2. Database Connectivity
```bash
mysql -h [DB-ENDPOINT] -u admin -p
SELECT COUNT(*) FROM users;
```

### 3. Monitoring & Alerts
```bash
# Verify CloudWatch metrics
# Check Lambda execution logs
# Confirm SNS notifications working
```

---

## Post-Recovery Checklist

- [ ] All services operational
- [ ] Data integrity verified
- [ ] Monitoring enabled
- [ ] Stakeholders notified
- [ ] Incident report created
- [ ] Root cause analysis scheduled
- [ ] Documentation updated

---

**Document Version:** 1.0  
**Last Updated:** $(date)  
**Next Review:** 3 months
