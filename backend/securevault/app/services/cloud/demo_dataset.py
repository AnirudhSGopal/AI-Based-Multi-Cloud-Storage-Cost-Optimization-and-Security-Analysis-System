"""
Curated Multi-Cloud Demo Dataset & 30-Day Cost Reduction Cycle.
Dedicated for demo user: anirudhsgopal18@gmai.com (and alias anirudhsgopal18@gmail.com).

Highlights:
- 3 Connected Cloud Providers: AWS, GCP, Azure
- 30-Day Cost Trend: Demonstrates a 54.5% cost reduction ($11,700/mo -> $5,250/mo)
  directly driven by applying the AI cost optimizer's recommendations.
- Realistic Multi-Cloud Discovered Resources & Service Breakdowns.
- High-impact AI Cost Optimization Recommendations with verified dollar savings.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any


from config.settings import PROVIDER_STORAGE_CAPACITY_GB, get_provider_storage_capacity


DEMO_EMAILS = {"anirudhsgopal18@gmai.com", "anirudhsgopal18@gmail.com"}

def is_demo_user(email: str) -> bool:
    try:
        from flask import current_app
        if current_app and not current_app.config.get("ENABLE_DEMO_DATA", True):
            return False
    except Exception:
        pass
    if not email:
        return False
    return email.strip().lower() in DEMO_EMAILS


def get_demo_accounts_data() -> List[Dict[str, Any]]:
    """Return standard demo account summaries with fixed storage capacity attribute."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": 901,
            "provider": "aws",
            "account_label": "AWS Production Primary (us-east-1)",
            "storage_size": get_provider_storage_capacity("aws"),
            "storage_size_gb": get_provider_storage_capacity("aws"),
            "status": "connected",
            "details": {
                "access_key_id": "AKIA9DEMOEXAMPLE9982",
                "region": "us-east-1",
            },
            "last_synced_at": now_iso,
        },
        {
            "id": 902,
            "provider": "gcp",
            "account_label": "GCP Analytics & Data Platform",
            "storage_size": get_provider_storage_capacity("gcp"),
            "storage_size_gb": get_provider_storage_capacity("gcp"),
            "status": "connected",
            "details": {
                "project_id": "cloudopt-enterprise-prod-01",
                "bigquery_dataset": "billing_export_prod",
                "has_service_account_json": True,
            },
            "last_synced_at": now_iso,
        },
        {
            "id": 903,
            "provider": "azure",
            "account_label": "Azure Corporate Workloads",
            "storage_size": get_provider_storage_capacity("azure"),
            "storage_size_gb": get_provider_storage_capacity("azure"),
            "status": "connected",
            "details": {
                "subscription_id": "sub-8841-92fa-azure-prod",
                "tenant_id": "tenant-0041-99af",
                "client_id": "app-cloudopt-analyzer",
            },
            "last_synced_at": now_iso,
        },
    ]


def get_30_day_chart_cycle() -> List[Dict[str, Any]]:
    """
    Generate a realistic 30-day cost cycle showing multi-cloud reduction.
    Includes natural weekday/weekend variations, mid-week ETL spikes,
    and clear milestone events where AI recommendations were executed.
    """
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=29)

    # 30-day detailed progression: (AWS, GCP, Azure, Milestone event, Phase)
    daily_details = [
        # Days 1-6 (Week 1 Baseline: Unoptimized instances & unattached disks)
        (164.20, 118.50, 122.30, None, "Baseline"),
        (168.80, 121.10, 124.70, None, "Baseline"),
        (171.40, 125.60, 126.90, "Mid-week ETL pipeline batch", "Baseline"),
        (167.30, 122.40, 123.50, None, "Baseline"),
        (163.50, 116.80, 120.20, None, "Baseline"),
        (154.20, 108.90, 114.60, "Weekend traffic dip", "Baseline"),
        # Days 7-12 (Week 2: Anomaly spend spike & scan initiated)
        (156.80, 110.40, 115.30, "Weekend traffic dip", "Baseline"),
        (166.70, 122.90, 124.10, None, "Baseline"),
        (170.50, 126.30, 127.80, None, "Baseline"),
        (176.40, 131.80, 133.20, "⚠️ Anomaly: BigQuery scan & orphaned snapshots", "Baseline"),
        (174.10, 129.50, 131.40, "🔍 CloudOpt AI Optimizer scan triggered", "Baseline"),
        (171.90, 127.20, 128.60, "📋 6 AI Cost Recommendations generated", "Baseline"),
        # Days 13-18 (Week 3: Rapid drop as primary recommendations are applied)
        (162.40, 120.10, 124.30, "⚡ Step 1: 800 GB unattached EBS/Managed disks purged", "Optimizing"),
        (152.10, 111.40, 116.80, "⚡ Step 2: AWS c5.4xlarge downsized to c5.xlarge", "Optimizing"),
        (144.60, 102.80, 109.50, "⚡ Step 3: Stopped GCP & Azure VMs decommissioned", "Optimizing"),
        (138.20, 96.50, 104.20, None, "Optimizing"),
        (131.50, 90.10, 97.40, "Weekend dip", "Optimizing"),
        (128.40, 86.80, 94.60, "Weekend dip", "Optimizing"),
        # Days 19-24 (Week 4: Storage lifecycle transitions & compute commitments active)
        (116.80, 78.40, 87.20, "⚡ Step 4: S3 & GCS Glacier/Coldline lifecycle active", "Optimizing"),
        (104.50, 69.20, 78.60, "⚡ Step 5: BigQuery daily partitioning & slot limits", "Optimizing"),
        (94.20, 61.80, 70.40, "⚡ Step 6: 1-Year Compute Savings Plans locked in", "Optimizing"),
        (87.60, 56.40, 64.90, "⚡ Step 7: Idle NAT Gateways & unused IPs purged", "Optimizing"),
        (83.10, 52.70, 60.30, None, "Optimizing"),
        (79.40, 49.80, 57.10, "Weekend dip", "Optimizing"),
        # Days 25-30 (Week 5: Lean, optimized steady-state)
        (78.20, 48.90, 55.80, "✅ Steady-state lean operation", "Optimized"),
        (76.50, 47.60, 54.20, None, "Optimized"),
        (77.90, 48.40, 55.10, None, "Optimized"),
        (75.80, 47.10, 53.60, None, "Optimized"),
        (74.90, 46.50, 52.80, None, "Optimized"),
        (74.20, 46.10, 52.40, "✅ Total 30-Day Reduction: 56.5% saved", "Optimized"),
    ]

    chart_points = []
    baseline_total = daily_details[0][0] + daily_details[0][1] + daily_details[0][2]

    for i, (aws, gcp, az, milestone, phase) in enumerate(daily_details):
        cur_date = start_date + timedelta(days=i)
        day_total = round(aws + gcp + az, 2)
        saved_vs_baseline = round(baseline_total - day_total, 2) if day_total < baseline_total else 0.0

        chart_points.append({
            "day": f"Day {i + 1}",
            "day_num": i + 1,
            "date": cur_date.strftime("%b %d"),
            "formatted_date": cur_date.strftime("%A, %b %d, %Y"),
            "full_date": cur_date.isoformat(),
            "AWS": round(aws, 2),
            "GCP": round(gcp, 2),
            "Azure": round(az, 2),
            "Total": day_total,
            "monthly_runrate": round(day_total * 30, 2),
            "saved_per_day": saved_vs_baseline,
            "milestone": milestone,
            "phase": phase,
            "storage_aws": get_provider_storage_capacity("aws"),
            "storage_gcp": get_provider_storage_capacity("gcp"),
            "storage_azure": get_provider_storage_capacity("azure"),
            "storage_total": sum(PROVIDER_STORAGE_CAPACITY_GB.values()),
            "storage_split": {"AWS": 40, "GCP": 30, "Azure": 30},
        })

    return chart_points


def validate_daily_storage_invariance(daily_trend: List[Dict[str, Any]]) -> bool:
    """
    Validate that storage capacity for every provider remains strictly invariant
    across all days in baseline, optimizing, and optimized phases.
    Raises AssertionError if any provider storage differs between days.
    """
    expected_aws = get_provider_storage_capacity("aws")
    expected_gcp = get_provider_storage_capacity("gcp")
    expected_azure = get_provider_storage_capacity("azure")
    expected_total = sum(PROVIDER_STORAGE_CAPACITY_GB.values())

    for idx, day in enumerate(daily_trend):
        d_name = day.get("day", f"Day {idx+1}")
        aws_val = day.get("storage_aws")
        gcp_val = day.get("storage_gcp")
        azure_val = day.get("storage_azure")
        total_val = day.get("storage_total")

        if aws_val != expected_aws:
            raise AssertionError(f"Storage invariance violation on {d_name} for AWS: expected {expected_aws} GB, got {aws_val} GB")
        if gcp_val != expected_gcp:
            raise AssertionError(f"Storage invariance violation on {d_name} for GCP: expected {expected_gcp} GB, got {gcp_val} GB")
        if azure_val != expected_azure:
            raise AssertionError(f"Storage invariance violation on {d_name} for Azure: expected {expected_azure} GB, got {azure_val} GB")
        if total_val != expected_total:
            raise AssertionError(f"Storage invariance violation on {d_name} for Total: expected {expected_total} GB, got {total_val} GB")

    return True


def get_demo_service_costs(provider: str) -> List[Dict[str, Any]]:
    """Return realistic monthly service breakdown costs for the provider."""
    provider = provider.lower()

    if provider == "aws":
        return [
            {"service": "Amazon EC2 (Compute)", "provider": "aws", "monthly_cost": 1420.50, "currency": "USD"},
            {"service": "Amazon S3 (Storage)", "provider": "aws", "monthly_cost": 480.00, "currency": "USD"},
            {"service": "Amazon RDS Aurora", "provider": "aws", "monthly_cost": 620.00, "currency": "USD"},
            {"service": "Amazon EBS Volumes", "provider": "aws", "monthly_cost": 180.00, "currency": "USD"},
            {"service": "CloudWatch & NAT Gateway", "provider": "aws", "monthly_cost": 125.00, "currency": "USD"},
            {"service": "AWS DynamoDB", "provider": "aws", "monthly_cost": 95.00, "currency": "USD"},
        ]
    elif provider == "gcp":
        return [
            {"service": "Compute Engine (VMs)", "provider": "gcp", "monthly_cost": 780.00, "currency": "USD"},
            {"service": "Google Cloud Storage", "provider": "gcp", "monthly_cost": 310.00, "currency": "USD"},
            {"service": "BigQuery Analytics", "provider": "gcp", "monthly_cost": 240.00, "currency": "USD"},
            {"service": "Google Kubernetes Engine", "provider": "gcp", "monthly_cost": 360.00, "currency": "USD"},
            {"service": "Cloud SQL Database", "provider": "gcp", "monthly_cost": 220.00, "currency": "USD"},
        ]
    elif provider == "azure":
        return [
            {"service": "Azure Virtual Machines", "provider": "azure", "monthly_cost": 890.00, "currency": "USD"},
            {"service": "Azure Blob Storage", "provider": "azure", "monthly_cost": 340.00, "currency": "USD"},
            {"service": "Azure SQL Database", "provider": "azure", "monthly_cost": 450.00, "currency": "USD"},
            {"service": "Azure Managed Disks", "provider": "azure", "monthly_cost": 120.00, "currency": "USD"},
            {"service": "Application Gateway & Logs", "provider": "azure", "monthly_cost": 110.00, "currency": "USD"},
        ]

    return []


def get_demo_resources(provider: str) -> List[Dict[str, Any]]:
    """Return realistic multi-cloud resources discovered for this account."""
    provider = provider.lower()

    if provider == "aws":
        return [
            {
                "resource_id": "i-09a8f7c1e34b9d012",
                "name": "prod-api-backend-c5xlarge",
                "resource_type": "ec2_instance",
                "provider": "aws",
                "region": "us-east-1",
                "status": "running",
                "metadata": {"instance_type": "c5.4xlarge", "avg_cpu_utilization": "8.4%", "right_size_target": "c5.xlarge"},
            },
            {
                "resource_id": "i-0bf39a1c44e980aa1",
                "name": "staging-worker-node-03",
                "resource_type": "ec2_instance",
                "provider": "aws",
                "region": "us-east-1",
                "status": "stopped",
                "metadata": {"instance_type": "m5.large", "days_stopped": 24},
            },
            {
                "resource_id": "vol-08f32ba97103gp3",
                "name": "unattached-db-snapshot-vol",
                "resource_type": "ebs_volume",
                "provider": "aws",
                "region": "us-east-1",
                "status": "unattached",
                "metadata": {"size_gb": 350, "volume_type": "gp3"},
            },
            {
                "resource_id": "s3://prod-analytics-datalake-raw",
                "name": "prod-analytics-datalake-raw",
                "resource_type": "s3_bucket",
                "provider": "aws",
                "region": "us-east-1",
                "status": "active",
                "metadata": {"size_gb": 4800, "has_lifecycle_policy": False, "encryption": "AES256"},
            },
            {
                "resource_id": "rds-aurora-cluster-main",
                "name": "rds-aurora-cluster-main",
                "resource_type": "rds_cluster",
                "provider": "aws",
                "region": "us-east-1",
                "status": "available",
                "metadata": {"engine": "aurora-postgresql", "instance_class": "db.r6g.xlarge"},
            },
            {
                "resource_id": "nat-09b183f081c79a",
                "name": "vpc-nat-gateway-us-east-1a",
                "resource_type": "nat_gateway",
                "provider": "aws",
                "region": "us-east-1",
                "status": "available",
                "metadata": {"idle_traffic": True},
            },
        ]
    elif provider == "gcp":
        return [
            {
                "resource_id": "gcp-vm-worker-analytics-02",
                "name": "worker-analytics-02",
                "resource_type": "gcp_instance",
                "provider": "gcp",
                "region": "us-central1-a",
                "status": "stopped",
                "metadata": {"machine_type": "n2-standard-8", "days_stopped": 18},
            },
            {
                "resource_id": "gcp-disk-temp-scratch-01",
                "name": "temp-scratch-disk-400gb",
                "resource_type": "gcp_disk",
                "provider": "gcp",
                "region": "us-central1-a",
                "status": "unattached",
                "metadata": {"size_gb": 400, "disk_type": "pd-ssd"},
            },
            {
                "resource_id": "gs://gcp-bi-backups-archive",
                "name": "gcp-bi-backups-archive",
                "resource_type": "gcs_bucket",
                "provider": "gcp",
                "region": "us-central1",
                "status": "active",
                "metadata": {"size_gb": 3200, "has_lifecycle_policy": False, "uniform_bucket_access": True},
            },
            {
                "resource_id": "gke-prod-cluster-apps",
                "name": "gke-prod-cluster-apps",
                "resource_type": "gke_cluster",
                "provider": "gcp",
                "region": "us-central1",
                "status": "running",
                "metadata": {"node_count": 4, "machine_type": "e2-standard-4"},
            },
            {
                "resource_id": "bq-dataset-billing-export",
                "name": "billing_export_prod",
                "resource_type": "bigquery_dataset",
                "provider": "gcp",
                "region": "US",
                "status": "active",
                "metadata": {"partitioning": "DAY", "uncompressed_queries_detected": True},
            },
        ]
    elif provider == "azure":
        return [
            {
                "resource_id": "vm-app-frontend-cluster-01",
                "name": "vm-frontend-cluster-01",
                "resource_type": "azure_vm",
                "provider": "azure",
                "region": "eastus",
                "status": "running",
                "metadata": {"vm_size": "Standard_D8s_v5", "avg_cpu_utilization": "11.2%"},
            },
            {
                "resource_id": "vm-legacy-reporting-old",
                "name": "vm-legacy-reporting-old",
                "resource_type": "azure_vm",
                "provider": "azure",
                "region": "eastus",
                "status": "deallocated",
                "metadata": {"vm_size": "Standard_E4s_v3", "days_stopped": 30},
            },
            {
                "resource_id": "disk-backup-unattached-450gb",
                "name": "disk-backup-unattached-450gb",
                "resource_type": "azure_disk",
                "provider": "azure",
                "region": "eastus",
                "status": "unattached",
                "metadata": {"size_gb": 450, "disk_tier": "Premium_LRS"},
            },
            {
                "resource_id": "stblob-prod-telemetry-logs",
                "name": "stblob-prod-telemetry-logs",
                "resource_type": "azure_storage_account",
                "provider": "azure",
                "region": "eastus",
                "status": "active",
                "metadata": {"size_gb": 2900, "has_lifecycle_policy": False, "access_tier": "Hot"},
            },
            {
                "resource_id": "sql-az-customer-db",
                "name": "sql-az-customer-db",
                "resource_type": "azure_sql",
                "provider": "azure",
                "region": "eastus",
                "status": "online",
                "metadata": {"service_tier": "GeneralPurpose", "vCores": 4},
            },
        ]

    return []


def get_demo_recommendations() -> List[Dict[str, Any]]:
    """Return high-impact AI optimization recommendations explaining the 30-day savings story."""
    return [
        {
            "id": "rec-demo-aws-rightsize-ec2",
            "category": "cost",
            "priority": "critical",
            "provider": "AWS",
            "title": "Right-size oversized EC2 c5.4xlarge instances to c5.xlarge",
            "description": "Instance 'i-09a8f7c1e34b9d012' has sustained average CPU utilization of 8.4% over 30 days. Downsizing to c5.xlarge retains 100% throughput performance.",
            "impact_statement": "Immediate compute savings of $1,429.50/mo with zero application downtime via rolling blue-green update.",
            "estimated_monthly_savings": 1429.50,
            "effort": "Low",
        },
        {
            "id": "rec-demo-multi-unattached-disks",
            "category": "storage",
            "priority": "critical",
            "provider": "AWS",
            "title": "Purge unattached EBS volumes & Azure Premium Disks (800 GB total)",
            "description": "Detected 350 GB unattached gp3 EBS volume in us-east-1 and 450 GB unattached Premium SSD in Azure East US orphaned from deleted staging environments.",
            "impact_statement": "Eliminating orphaned storage blocks prevents continuous recurring volume rental fees, saving $590.00/mo.",
            "estimated_monthly_savings": 590.00,
            "effort": "Low",
        },
        {
            "id": "rec-demo-s3-gcs-lifecycle",
            "category": "storage",
            "priority": "high",
            "provider": "AWS",
            "title": "Configure automated Lifecycle Transitions to Glacier & Coldline",
            "description": "Bucket 's3://prod-analytics-datalake-raw' (4.8 TB) and 'gs://gcp-bi-backups-archive' (3.2 TB) retain objects older than 90 days in standard hot storage tiers.",
            "impact_statement": "Automating transition to Glacier Instant Retrieval and GCP Coldline cuts object storage unit costs by 68%, saving $780.00/mo.",
            "estimated_monthly_savings": 780.00,
            "effort": "Medium",
        },
        {
            "id": "rec-demo-stopped-vms",
            "category": "cost",
            "priority": "medium",
            "provider": "GCP",
            "title": "Decommission stopped GCP & Azure VMs incurring persistent disk fees",
            "description": "Instances 'gcp-vm-worker-analytics-02' (stopped 18 days) and 'vm-legacy-reporting-old' (stopped 30 days) continue billing reserved high-speed SSD storage.",
            "impact_statement": "Snapshotting VM configurations to cold storage and terminating the stopped VM shells recovers $340.00/mo.",
            "estimated_monthly_savings": 340.00,
            "effort": "Low",
        },
        {
            "id": "rec-demo-savings-plans",
            "category": "cost",
            "priority": "critical",
            "provider": "AWS",
            "title": "Commit steady-state workloads to 1-Year Compute Savings Plans",
            "description": "Baseline predictable multi-cloud compute workloads qualify for 1-year committed use discounts across AWS EC2 and Azure VMs.",
            "impact_statement": "Securing 1-year flexible compute commitments reduces hourly rates by 38%, unlocking $1,860.00/mo in savings.",
            "estimated_monthly_savings": 1860.00,
            "effort": "Medium",
        },
        {
            "id": "rec-demo-bigquery-optimize",
            "category": "cost",
            "priority": "medium",
            "provider": "GCP",
            "title": "Optimize BigQuery Partitioning & Query Slot Reservations",
            "description": "Daily scheduled ETL queries scan entire unpartitioned billing dataset tables, causing high on-demand analysis charges.",
            "impact_statement": "Enforcing ingestion-time daily table partitioning reduces processed data scan volume by 82%, saving $450.00/mo.",
            "estimated_monthly_savings": 450.00,
            "effort": "Medium",
        },
    ]
