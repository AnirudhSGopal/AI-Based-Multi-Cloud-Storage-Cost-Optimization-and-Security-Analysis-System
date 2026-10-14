import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, r"c:\Users\ANIRUDHMALU\Documents\cloudProject\backend\securevault")
scripts_dir = str(Path(sys.executable).parent)
os.environ["PATH"] = scripts_dir + os.pathsep + os.environ.get("PATH", "")

from app.services.cloud import optimizer
from app.services.scanner.static_analyzer import analyze_repository
from app.services.scanner.dependency_auditor import audit_dependencies
from app.models.scan import SeverityEnum, FindingTypeEnum


def run_cost_evaluations():
    print("=" * 70)
    print("OBJECTIVE 1: COST OPTIMIZER EVALUATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # Scenario 1: Comprehensive Multi-Cloud Enterprise Environment (AWS + Azure + GCP)
    # -------------------------------------------------------------
    # AWS Resources (4 resources): 1 stopped EC2, 1 unattached EBS, 1 S3 without lifecycle, 1 oversized EC2
    # Azure Resources (3 resources): 1 stopped VM, 1 unattached Azure disk, 1 storage account without lifecycle
    # GCP Resources (3 resources): 1 large GCP VM (heuristic), 1 unattached GCP disk, 1 GCS bucket without lifecycle
    # Total Resources = 10 (4 AWS, 3 Azure, 3 GCP)
    multi_cloud_resources = [
        # AWS
        {"resource_id": "i-0a1b2c3d4e5f67890", "resource_type": "ec2_instance", "provider": "aws", "status": "stopped", "metadata": {"instance_type": "t3.medium", "estimated_monthly_cost": 45.0}},
        {"resource_id": "vol-0123456789abcdef0", "resource_type": "ebs_volume", "provider": "aws", "status": "unattached", "metadata": {"size_gb": 200}},
        {"resource_id": "aws-app-logs-bucket", "resource_type": "s3_bucket", "provider": "aws", "metadata": {"has_lifecycle_policy": False}},
        {"resource_id": "i-0987654321fedcba1", "resource_type": "ec2_instance", "provider": "aws", "status": "running", "metadata": {"instance_type": "c5.2xlarge", "cpu_utilization": 8.4, "estimated_monthly_cost": 280.0}},
        # Azure
        {"resource_id": "vm-prod-app-eastus", "resource_type": "azure_vm", "provider": "azure", "status": "deallocated", "metadata": {"vm_size": "Standard_D4s_v5", "estimated_monthly_cost": 140.0}},
        {"resource_id": "disk-orphan-backup", "resource_type": "azure_disk", "provider": "azure", "status": "unattached", "metadata": {"size_gb": 500}},
        {"resource_id": "azstorageaccountcold", "resource_type": "azure_storage_account", "provider": "azure", "metadata": {"has_lifecycle_policy": False}},
        # GCP
        {"resource_id": "gcp-analytics-node-1", "resource_type": "gcp_instance", "provider": "gcp", "status": "running", "metadata": {"machine_type": "n2-standard-16", "estimated_monthly_cost": 485.0}},
        {"resource_id": "gcp-disk-temp-scratch", "resource_type": "gcp_disk", "provider": "gcp", "status": "unattached", "metadata": {"size_gb": 150}},
        {"resource_id": "gcs-raw-telemetry-data", "resource_type": "gcs_bucket", "provider": "gcp", "metadata": {"has_lifecycle_rules": False, "has_lifecycle_policy": False}}
    ]

    # Cost Data with MoM Cost Spike on AWS, plus Compute, Storage, Networking across AWS, Azure, GCP
    multi_cloud_costs = [
        # AWS Costs
        {"service": "Amazon Elastic Compute Cloud - Compute", "monthly_cost": 1200.00, "provider": "aws"},
        {"service": "Amazon Elastic Compute Cloud - Compute", "monthly_cost": 1750.00, "provider": "aws"}, # Cost Spike +$550 (+45.8%)
        {"service": "Amazon Simple Storage Service", "monthly_cost": 420.00, "provider": "aws"},
        {"service": "AWS Data Transfer / CloudFront", "monthly_cost": 210.00, "provider": "aws"},
        # Azure Costs
        {"service": "Virtual Machines", "monthly_cost": 850.00, "provider": "azure"},
        {"service": "Azure Blob Storage", "monthly_cost": 310.00, "provider": "azure"},
        {"service": "Azure Virtual Network / Bandwidth", "monthly_cost": 160.00, "provider": "azure"},
        # GCP Costs
        {"service": "Compute Engine", "monthly_cost": 950.00, "provider": "gcp"},
        {"service": "Cloud Storage", "monthly_cost": 280.00, "provider": "gcp"},
        {"service": "Cloud Networking", "monthly_cost": 140.00, "provider": "gcp"}
    ]

    recs = optimizer._run_rule_checks(multi_cloud_resources, multi_cloud_costs)
    
    # Calculate original total cost (using latest snapshot for each service)
    # AWS: 1750 + 420 + 210 = 2380.00
    # Azure: 850 + 310 + 160 = 1320.00
    # GCP: 950 + 280 + 140 = 1370.00
    # Total monthly cost = 5070.00
    total_savings = sum(r["estimated_monthly_savings"] for r in recs)

    print(f"Total Recommendations: {len(recs)}")
    print(f"Total Estimated Savings: ${total_savings:.2f}")
    for idx, r in enumerate(recs, 1):
        print(f"{idx}. [{r['provider'].upper()}] ({r['priority'].upper()}) {r['title']} -> ${r['estimated_monthly_savings']:.2f}/mo (Category: {r['category']})")

    # 5 Distinct Scenarios:
    scenarios = [
        {
            "name": "Scenario 1: Idle & Stopped Compute Instances",
            "resources": [
                {"resource_id": "ec2-dev-test-01", "resource_type": "ec2_instance", "provider": "aws", "status": "stopped", "metadata": {"instance_type": "t3.large"}},
                {"resource_id": "azure-qa-vm-02", "resource_type": "azure_vm", "provider": "azure", "status": "deallocated", "metadata": {"vm_size": "Standard_B2s"}},
                {"resource_id": "gcp-stage-vm-03", "resource_type": "gcp_instance", "provider": "gcp", "status": "off", "metadata": {"machine_type": "e2-standard-2"}}
            ],
            "costs": [
                {"service": "Amazon EC2", "monthly_cost": 180.00, "provider": "aws"},
                {"service": "Azure Virtual Machines", "monthly_cost": 120.00, "provider": "azure"},
                {"service": "GCP Compute Engine", "monthly_cost": 95.00, "provider": "gcp"}
            ]
        },
        {
            "name": "Scenario 2: Unattached EBS & Persistent Disks (Storage Waste)",
            "resources": [
                {"resource_id": "vol-orphan-500gb", "resource_type": "ebs_volume", "provider": "aws", "status": "unattached", "metadata": {"size_gb": 500}},
                {"resource_id": "disk-unattached-250gb", "resource_type": "azure_disk", "provider": "azure", "status": "unused", "metadata": {"size_gb": 250}},
                {"resource_id": "gcp-orphan-disk-1tb", "resource_type": "gcp_disk", "provider": "gcp", "status": "available", "metadata": {"size_gb": 1000}}
            ],
            "costs": [
                {"service": "Amazon EBS", "monthly_cost": 250.00, "provider": "aws"},
                {"service": "Azure Managed Disks", "monthly_cost": 125.00, "provider": "azure"},
                {"service": "GCP Persistent Disk", "monthly_cost": 300.00, "provider": "gcp"}
            ]
        },
        {
            "name": "Scenario 3: Missing Storage Lifecycle Tiering Policies",
            "resources": [
                {"resource_id": "s3-raw-data-bucket", "resource_type": "s3_bucket", "provider": "aws", "metadata": {"has_lifecycle_policy": False}},
                {"resource_id": "azure-blob-backup-store", "resource_type": "azure_storage_account", "provider": "azure", "metadata": {"has_lifecycle_policy": False}},
                {"resource_id": "gcs-ml-dataset-bucket", "resource_type": "gcs_bucket", "provider": "gcp", "metadata": {"has_lifecycle_policy": False}}
            ],
            "costs": [
                {"service": "Amazon Simple Storage Service (S3)", "monthly_cost": 650.00, "provider": "aws"},
                {"service": "Azure Blob Storage", "monthly_cost": 480.00, "provider": "azure"},
                {"service": "Google Cloud Storage (GCS)", "monthly_cost": 390.00, "provider": "gcp"}
            ]
        },
        {
            "name": "Scenario 4: Month-over-Month Anomalous Cost Spikes (>20%)",
            "resources": [
                {"resource_id": "i-prod-web-cluster", "resource_type": "ec2_instance", "provider": "aws", "status": "running", "metadata": {"instance_type": "m5.large"}}
            ],
            "costs": [
                {"service": "Amazon EC2", "monthly_cost": 1500.00, "provider": "aws"},
                {"service": "Amazon EC2", "monthly_cost": 2750.00, "provider": "aws"}, # +$1250 spike (+83.3%)
                {"service": "Azure Virtual Machines", "monthly_cost": 800.00, "provider": "azure"},
                {"service": "Azure Virtual Machines", "monthly_cost": 1350.00, "provider": "azure"}, # +$550 spike (+68.75%)
                {"service": "GCP BigQuery", "monthly_cost": 400.00, "provider": "gcp"},
                {"service": "GCP BigQuery", "monthly_cost": 920.00, "provider": "gcp"} # +$520 spike (+130.0%)
            ]
        },
        {
            "name": "Scenario 5: Compute Right-Sizing & FinOps Commitments (CUD/RI, Egress, Storage)",
            "resources": [
                {"resource_id": "i-underutilized-app", "resource_type": "ec2_instance", "provider": "aws", "status": "running", "metadata": {"instance_type": "c5.4xlarge", "cpu_utilization": 6.8, "estimated_monthly_cost": 450.0}},
                {"resource_id": "gcp-oversized-batch", "resource_type": "gcp_instance", "provider": "gcp", "status": "running", "metadata": {"machine_type": "n2-standard-32", "estimated_monthly_cost": 820.0}}
            ],
            "costs": [
                {"service": "Amazon Elastic Compute Cloud", "monthly_cost": 2400.00, "provider": "aws"},
                {"service": "AWS CloudFront & Data Transfer", "monthly_cost": 600.00, "provider": "aws"},
                {"service": "Google Cloud Storage", "monthly_cost": 500.00, "provider": "gcp"},
                {"service": "Azure Virtual Machines", "monthly_cost": 1800.00, "provider": "azure"}
            ]
        }
    ]

    print("\n" + "=" * 70)
    print("DETAILED 5 TEST CASES EVALUATION")
    print("=" * 70)
    for s_idx, sc in enumerate(scenarios, 1):
        s_recs = optimizer._run_rule_checks(sc["resources"], sc["costs"])
        # Calculate current monthly cost
        # Take latest unique service costs
        latest_service_costs = {}
        for c in sc["costs"]:
            latest_service_costs[(c["provider"], c["service"])] = c["monthly_cost"]
        orig_cost = sum(latest_service_costs.values())
        savings = sum(r["estimated_monthly_savings"] for r in s_recs)
        opt_cost = max(0.0, orig_cost - savings)
        rules_triggered = list({r["id"].split("-")[1] for r in s_recs})

        print(f"\n--- {sc['name']} ---")
        print(f"Original Monthly Cost: ${orig_cost:.2f}")
        print(f"Triggered Rule Types: {rules_triggered}")
        print(f"Recommendations Count: {len(s_recs)}")
        for r in s_recs:
            print(f"  * [{r['id']}] {r['title']} -> Savings: ${r['estimated_monthly_savings']:.2f}/mo (Category: {r['category']})")
        print(f"Total Estimated Savings: ${savings:.2f}")
        print(f"Optimized Monthly Cost: ${opt_cost:.2f}")


def run_security_evaluations():
    print("\n" + "=" * 70)
    print("OBJECTIVE 2: SECURITY SCANNER EVALUATION")
    print("=" * 70)

    # We will build a controlled test repository with representative vulnerabilities,
    # and execute 4 consecutive scan cycles:
    # Scan 1: Baseline (Unremediated)
    # Scan 2: Remediation of Critical Vulnerabilities
    # Scan 3: Remediation of High Vulnerabilities
    # Final Scan: Remediation of Medium & Low Vulnerabilities (Clean state)

    temp_repo = tempfile.mkdtemp(prefix="securevault_eval_repo_")
    repo_path = Path(temp_repo)

    # 1. Setup Initial Test Project Files with intentional vulnerabilities across all categories
    # Insecure Code & Secrets in Python
    (repo_path / "app").mkdir(parents=True, exist_ok=True)
    
    # File 1: auth_service.py (SEC001, SEC002, SEC004, CODE014)
    (repo_path / "app" / "auth_service.py").write_text("""
import os
import hashlib

# Hardcoded AWS Credentials (SEC001, SEC002)
AWS_ACCESS_KEY = "AKIA1234567890ABCDEF"
AWS_SECRET_KEY = "aws_secret_key = 'abcdefghijklmnopqrstuvwxyz0123456789ABCD'"

# Hardcoded JWT & Password (SEC004, CODE014)
jwt_secret = "super_secret_jwt_signing_key_123456"
db_password = "SuperAdminPassword2026!"

def hash_user_password(pwd):
    # Weak MD5 hash (CODE011)
    return hashlib.md5(pwd.encode()).hexdigest()
""", encoding="utf-8")

    # File 2: db_service.py (SEC005, CODE003, CODE004, CODE009, CODE010)
    (repo_path / "app" / "db_service.py").write_text("""
import pickle
import yaml
import sqlite3

# Hardcoded Database Connection String with Password (SEC005)
DB_URI = "postgres://admin:MasterSecretPwd999@db.production.internal:5432/securevault"

def get_user(user_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    # SQL Injection via String Formatting (CODE003)
    cursor.execute("SELECT * FROM users WHERE id = '%s'" % user_id)
    # SQL Injection via f-string (CODE004)
    query = f"SELECT * FROM accounts WHERE user_id = '{user_id}'"
    return cursor.execute(query).fetchall()

def load_payload(raw_data):
    # Insecure Deserialization (CODE009)
    data = pickle.loads(raw_data)
    # Insecure YAML loading (CODE010)
    config = yaml.load(raw_data)
    return data, config
""", encoding="utf-8")

    # File 3: api_routes.py (SEC003, SEC006, SEC008, CODE001, CODE002, CODE005, CODE006, CODE015)
    (repo_path / "app" / "api_routes.py").write_text("""
import os
import subprocess

# Generic API Key & Tokens (SEC003, SEC006, SEC008)
api_key = "AIzaSyD9876543210ZYXWVUTSRQPONMLKJIHGF"
github_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
google_api_key = "AIzaSyDummyTestKeyExampleNotReal0000000"

# Debug mode in production (CODE015)
DEBUG = True

def execute_user_script(script_str, command_str):
    # Dangerous eval/exec (CODE001, CODE002)
    result = eval(script_str)
    exec(script_str)
    # Shell Injection (CODE005, CODE006)
    os.system("echo " + command_str)
    subprocess.run("ls " + command_str, shell=True)
    return result
""", encoding="utf-8")

    # File 4: web_views.py (CODE007, CODE012, CODE013)
    (repo_path / "app" / "web_views.py").write_text("""
import hashlib
from jinja2 import Markup

def render_comment(user_html):
    # XSS via Markup (CODE007)
    safe_content = Markup(user_html)
    return safe_content

def calculate_checksum(file_content):
    # Weak SHA-1 (CODE012)
    return hashlib.sha1(file_content).hexdigest()

def read_user_file(request):
    # Path Traversal open (CODE013)
    f = open(request.args.get('path'))
    return f.read()
""", encoding="utf-8")

    # File 5: frontend_component.jsx (CODE008)
    (repo_path / "app" / "Component.jsx").write_text("""
import React from 'react';

export function UnsafeView({ dynamicHtml }) {
    // XSS innerHTML assignment (CODE008)
    document.getElementById('content').innerHTML = dynamicHtml;
    return <div id="content" />;
}
""", encoding="utf-8")

    # File 6: requirements.txt (Dependencies with known CVEs)
    (repo_path / "requirements.txt").write_text("""
flask==2.0.1
jinja2==2.11.3
requests==2.25.1
urllib3==1.26.4
cryptography==3.3.2
""", encoding="utf-8")

    # File 7: package.json (Node.js dependencies)
    (repo_path / "package.json").write_text(json.dumps({
        "name": "test-eval-app",
        "version": "1.0.0",
        "dependencies": {
            "axios": "0.21.1",
            "lodash": "4.17.15"
        }
    }, indent=2), encoding="utf-8")

    def run_full_scan(scan_label: str):
        static_findings, stats = analyze_repository(str(repo_path))
        dependency_report = audit_dependencies(str(repo_path))
        dep_findings = dependency_report.findings
        all_findings = static_findings + dep_findings

        severity_counts = {s: 0 for s in SeverityEnum}
        finding_types = {t: 0 for t in FindingTypeEnum}
        rules_triggered = []

        for f in all_findings:
            sev = f["severity"]
            ftype = f["finding_type"]
            severity_counts[sev] += 1
            finding_types[ftype] += 1
            rules_triggered.append(f["rule_id"])

        pip_findings = [f for f in dep_findings if f["rule_id"].startswith("DEP-PY-")]
        npm_findings = [f for f in dep_findings if f["rule_id"].startswith("DEP-JS-")]
        maven_findings = [
            f for f in dep_findings
            if f["rule_id"].startswith("DEP-MAVEN-")
            and f.get("file_path", "").endswith("pom.xml")
        ]
        gradle_findings = [
            f for f in dep_findings
            if f["rule_id"].startswith("DEP-MAVEN-")
            and f.get("file_path", "").endswith((".gradle", ".gradle.kts"))
        ]

        print(f"\n=======================================================")
        print(f"{scan_label.upper()}")
        print(f"=======================================================")
        print(f"Files Scanned: {stats.files_scanned}")
        print(f"Lines Scanned: {stats.lines_scanned}")
        print(f"Total Security Findings: {len(all_findings)}")
        print(f"  - Critical: {severity_counts[SeverityEnum.CRITICAL]}")
        print(f"  - High:     {severity_counts[SeverityEnum.HIGH]}")
        print(f"  - Medium:   {severity_counts[SeverityEnum.MEDIUM]}")
        print(f"  - Low:      {severity_counts[SeverityEnum.LOW]}")
        print(f"  - Info:     {severity_counts[SeverityEnum.INFO]}")
        print(f"Finding Types:")
        print(f"  - Secrets (SEC): {finding_types.get(FindingTypeEnum.SECRET, 0)}")
        print(f"  - Insecure Code (CODE): {finding_types.get(FindingTypeEnum.CODE_PATTERN, 0)}")
        print(f"  - Dependencies (DEP): {finding_types.get(FindingTypeEnum.DEPENDENCY, 0)}")
        print(f"    * pip-audit: {len(pip_findings)}")
        print(f"    * npm-audit: {len(npm_findings)}")
        print(f"    * Maven: {len(maven_findings)}")
        print(f"    * Gradle: {len(gradle_findings)}")
        print(f"Dependency Coverage: {dependency_report.coverage}")
        print("Assessment is partial; no overall security score is calculated.")
        print(f"Triggered Rules ({len(rules_triggered)}): {rules_triggered}")
        return {
            "total": len(all_findings),
            "critical": severity_counts[SeverityEnum.CRITICAL],
            "high": severity_counts[SeverityEnum.HIGH],
            "medium": severity_counts[SeverityEnum.MEDIUM],
            "low": severity_counts[SeverityEnum.LOW],
            "rules": rules_triggered,
            "files": stats.files_scanned,
            "lines": stats.lines_scanned,
            "secrets": finding_types.get(FindingTypeEnum.SECRET, 0),
            "insecure_code": finding_types.get(FindingTypeEnum.CODE_PATTERN, 0),
            "pip_count": len(pip_findings),
            "npm_count": len(npm_findings),
            "maven_count": len(maven_findings),
            "gradle_count": len(gradle_findings),
            "coverage": dependency_report.coverage,
        }

    # RUN SCAN 1: BEFORE REMEDIATION
    s1 = run_full_scan("Scan 1 — Before remediation")

    # REMEDIATION PHASE 1: Fix All CRITICAL Vulnerabilities (SEC001, SEC002, SEC005, SEC006, CODE003, CODE004, CODE009)
    (repo_path / "app" / "auth_service.py").write_text("""
import os
import hashlib

# Remediated: Loaded from environment variables (SEC001, SEC002 fixed)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Hardcoded JWT & Password (still present for next phase: SEC004, CODE014)
jwt_secret = "super_secret_jwt_signing_key_123456"
db_password = "SuperAdminPassword2026!"

def hash_user_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()
""", encoding="utf-8")

    (repo_path / "app" / "db_service.py").write_text("""
import os
import json
import yaml
import sqlite3

# Remediated: Database URI from environment (SEC005 fixed)
DB_URI = os.getenv("DATABASE_URL")

def get_user(user_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    # Remediated: Parameterized queries (CODE003, CODE004 fixed)
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    cursor.execute("SELECT * FROM accounts WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def load_payload(raw_data):
    # Remediated: Safe JSON parsing (CODE009 fixed)
    data = json.loads(raw_data)
    # Still insecure yaml (CODE010 for next phase)
    config = yaml.load(raw_data)
    return data, config
""", encoding="utf-8")

    (repo_path / "app" / "api_routes.py").write_text("""
import os
import subprocess

# Remediated: GitHub token removed (SEC006 fixed)
github_token = os.getenv("GITHUB_TOKEN")
# Still present for next phase: SEC003, SEC008
api_key = "AIzaSyD9876543210ZYXWVUTSRQPONMLKJIHGF"
google_api_key = "AIzaSyDummyTestKeyExampleNotReal0000000"

DEBUG = True

def execute_user_script(script_str, command_str):
    result = eval(script_str)
    exec(script_str)
    os.system("echo " + command_str)
    subprocess.run("ls " + command_str, shell=True)
    return result
""", encoding="utf-8")

    # RUN SCAN 2: AFTER REMEDIATING CRITICAL FINDINGS
    s2 = run_full_scan("Scan 2 — After remediation (Critical fixed)")

    # REMEDIATION PHASE 2: Fix All HIGH Vulnerabilities (SEC003, SEC004, SEC008, CODE001, CODE002, CODE005, CODE006, CODE007, CODE010, CODE013, CODE014, pip dependencies)
    (repo_path / "app" / "auth_service.py").write_text("""
import os
import hashlib

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Remediated: Secrets in environment (SEC004, CODE014 fixed)
jwt_secret = os.getenv("JWT_SECRET_KEY")
db_password = os.getenv("DB_PASSWORD")

def hash_user_password(pwd):
    # MD5 still present for next phase (CODE011)
    return hashlib.md5(pwd.encode()).hexdigest()
""", encoding="utf-8")

    (repo_path / "app" / "db_service.py").write_text("""
import os
import json
import yaml
import sqlite3

DB_URI = os.getenv("DATABASE_URL")

def get_user(user_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchall()

def load_payload(raw_data):
    data = json.loads(raw_data)
    # Remediated: safe_load (CODE010 fixed)
    config = yaml.safe_load(raw_data)
    return data, config
""", encoding="utf-8")

    (repo_path / "app" / "api_routes.py").write_text("""
import os
import subprocess
import shlex

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
# Remediated: API keys from environment (SEC003, SEC008 fixed)
api_key = os.getenv("API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")
github_token = os.getenv("GITHUB_TOKEN")

# Still present for final phase (CODE015)
DEBUG = True

def execute_user_script(script_str, command_str):
    # Remediated: Removed eval/exec, use safe subprocess with shell=False (CODE001, CODE002, CODE005, CODE006 fixed)
    cmd = ["echo", command_str]
    subprocess.run(cmd, shell=False, check=True)
    return True
""", encoding="utf-8")

    (repo_path / "app" / "web_views.py").write_text("""
import hashlib
import os
from markupsafe import escape

def render_comment(user_html):
    # Remediated: HTML escaping (CODE007 fixed)
    return escape(user_html)

def calculate_checksum(file_content):
    # Still SHA-1 for next phase (CODE012)
    return hashlib.sha1(file_content).hexdigest()

def read_user_file(file_path):
    # Remediated: Path validation (CODE013 fixed)
    base_dir = os.path.abspath("/safe/base/dir")
    target = os.path.abspath(os.path.join(base_dir, file_path))
    if not target.startswith(base_dir):
        raise ValueError("Access denied")
    with open(target, "r") as f:
        return f.read()
""", encoding="utf-8")

    # Upgrade requirements.txt to latest patched versions
    (repo_path / "requirements.txt").write_text("""
flask>=3.0.3
jinja2>=3.1.4
requests>=2.32.0
urllib3>=2.2.2
cryptography>=42.0.8
""", encoding="utf-8")

    # RUN SCAN 3: AFTER FURTHER REMEDIATION (High fixed)
    s3 = run_full_scan("Scan 3 — After further remediation (High fixed)")

    # REMEDIATION PHASE 3: Fix All MEDIUM & LOW Vulnerabilities (CODE008, CODE011, CODE012, CODE015, npm dependencies)
    (repo_path / "app" / "auth_service.py").write_text("""
import os
import hashlib

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
jwt_secret = os.getenv("JWT_SECRET_KEY")
db_password = os.getenv("DB_PASSWORD")

def hash_user_password(pwd):
    # Remediated: SHA-256 (CODE011 fixed)
    return hashlib.sha256(pwd.encode()).hexdigest()
""", encoding="utf-8")

    (repo_path / "app" / "api_routes.py").write_text("""
import os
import subprocess

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
api_key = os.getenv("API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")
github_token = os.getenv("GITHUB_TOKEN")

# Remediated: Debug mode disabled in code (CODE015 fixed)
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

def execute_user_script(script_str, command_str):
    cmd = ["echo", command_str]
    subprocess.run(cmd, shell=False, check=True)
    return True
""", encoding="utf-8")

    (repo_path / "app" / "web_views.py").write_text("""
import hashlib
import os
from markupsafe import escape

def render_comment(user_html):
    return escape(user_html)

def calculate_checksum(file_content):
    # Remediated: SHA-256 (CODE012 fixed)
    return hashlib.sha256(file_content).hexdigest()

def read_user_file(file_path):
    base_dir = os.path.abspath("/safe/base/dir")
    target = os.path.abspath(os.path.join(base_dir, file_path))
    if not target.startswith(base_dir):
        raise ValueError("Access denied")
    with open(target, "r") as f:
        return f.read()
""", encoding="utf-8")

    (repo_path / "app" / "Component.jsx").write_text("""
import React from 'react';

export function SafeView({ dynamicText }) {
    // Remediated: textContent / safe React element (CODE008 fixed)
    return <div id="content">{dynamicText}</div>;
}
""", encoding="utf-8")

    (repo_path / "package.json").write_text(json.dumps({
        "name": "test-eval-app",
        "version": "1.0.0",
        "dependencies": {
            "axios": "^1.7.4",
            "lodash": "^4.17.21"
        }
    }, indent=2), encoding="utf-8")

    # RUN FINAL SCAN: CLEAN STATE
    s4 = run_full_scan("Final scan — Clean remediated repository")

    # Clean up temp repository
    shutil.rmtree(temp_repo, ignore_errors=True)

if __name__ == "__main__":
    run_cost_evaluations()
    run_security_evaluations()
