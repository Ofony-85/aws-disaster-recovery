# Cost Analysis - AWS Disaster Recovery System

## Monthly Cost Breakdown

### Compute Resources
| Resource | Specification | Hours/Month | Rate | Monthly Cost |
|----------|--------------|-------------|------|--------------|
| EC2 (Primary) | t2.micro | 730 | $0.0116/hr | $8.47 |
| RDS (Primary) | db.t3.micro | 730 | $0.017/hr | $12.41 |
| **Compute Total** | | | | **$20.88** |

### Storage Costs
| Resource | Size | Rate | Monthly Cost |
|----------|------|------|--------------|
| RDS Storage | 20 GB | $0.115/GB | $2.30 |
| RDS Snapshots | ~140 GB | $0.095/GB | $13.30 |
| EBS Volumes | 8 GB | $0.10/GB | $0.80 |
| AMI Snapshots | ~56 GB | $0.05/GB | $2.80 |
| S3 Primary | 1 GB | $0.023/GB | $0.023 |
| S3 DR Replica | 1 GB | $0.023/GB | $0.023 |
| **Storage Total** | | | **$19.25** |

### Data Transfer
| Transfer Type | Volume | Rate | Monthly Cost |
|---------------|--------|------|--------------|
| S3 CRR | 1 GB | $0.02/GB | $0.02 |
| RDS Snapshot Copy | 20 GB/day | $0.02/GB | $12.00 |
| AMI Copy | 8 GB/day | $0.02/GB | $4.80 |
| **Transfer Total** | | | **$16.82** |

### Lambda & Monitoring
| Service | Invocations | Rate | Monthly Cost |
|---------|-------------|------|--------------|
| Lambda Executions | ~500/month | $0.20/1M | $0.10 |
| Lambda Duration | ~10,000 GB-sec | $0.0000166667 | $0.17 |
| CloudWatch Logs | 1 GB | $0.50/GB | $0.50 |
| SNS Notifications | ~200/month | $0.50/1M | $0.10 |
| **Monitoring Total** | | | **$0.87** |

---

## Total Monthly Cost

| Category | Cost |
|----------|------|
| Compute | $20.88 |
| Storage | $19.25 |
| Data Transfer | $16.82 |
| Monitoring | $0.87 |
| **TOTAL** | **$57.82** |

---

## Cost Optimization Strategies

### Implemented
✅ **7-Day Retention:** Limits storage costs  
✅ **Lifecycle Policies:** Transitions old S3 versions  
✅ **Automated Cleanup:** Removes test resources  
✅ **t2/t3.micro:** Smallest viable instance types  

---

**Analysis Date:** $(date)  
**Next Review:** Monthly
