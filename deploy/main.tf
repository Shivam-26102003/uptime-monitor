# -----------------------------------------------------------------------------
# Deployment Sketch (hypothetical / illustrative — NOT applied by CI)
#
# Goal: host the same three-tier MVP on AWS with the least moving parts.
#   - RDS Postgres           -> managed database (the one piece worth not self-hosting)
#   - ECS Fargate (backend)  -> the FastAPI + scheduler container
#   - S3 + CloudFront (front) -> the static Vite build behind a CDN
#
# This is intentionally terse: it shows topology and wiring, not production
# hardening (no multi-AZ, secrets manager, WAF, autoscaling policies, etc.).
# -----------------------------------------------------------------------------

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# --- 1. Managed Postgres ------------------------------------------------------
resource "aws_db_instance" "uptime" {
  identifier          = "uptime-monitor-db"
  engine              = "postgres"
  engine_version      = "16"
  instance_class      = "db.t4g.micro"
  allocated_storage   = 20
  db_name             = "uptime"
  username            = "uptime"
  password            = var.db_password # from TF_VAR / secrets store, not committed
  skip_final_snapshot = true
}

# --- 2. Backend on ECS Fargate ------------------------------------------------
# The backend image is pushed to ECR; the scheduler lives inside the same
# container, so a single always-on task both serves the API and runs the
# 60s health-check loop. One task is enough at this scale.
resource "aws_ecs_cluster" "uptime" {
  name = "uptime-monitor"
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "uptime-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${var.ecr_repo_url}:latest"
      essential = true
      portMappings = [{ containerPort = 8000 }]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://uptime:${var.db_password}@${aws_db_instance.uptime.address}:5432/uptime"
        }
      ]
    }
  ])
}

# An ALB (omitted here for brevity) fronts the ECS service on :8000 and gives
# the backend a stable DNS name for CloudFront's /api/* behavior to target.

# --- 3. Frontend on S3 + CloudFront ------------------------------------------
# `npm run build` output is synced to this bucket. CloudFront serves the static
# assets and routes /api/* to the backend ALB (same single-origin pattern the
# local nginx uses), so the browser still only talks to one host.
resource "aws_s3_bucket" "frontend" {
  bucket = "uptime-monitor-frontend"
}

# variables ------------------------------------------------------------------
variable "db_password" {
  type      = string
  sensitive = true
}

variable "ecr_repo_url" {
  type = string
}
