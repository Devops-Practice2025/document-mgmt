resource "aws_security_group" "rds" {
  name_prefix = "${local.name}-rds"
  description = "MySQL access from EKS"
  vpc_id      = module.vpc.vpc_id

  tags = {
    Name = "${local.name}-rds"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_egress_rule" "rds_egress" {
  security_group_id = aws_security_group.rds.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_db_instance" "mysql" {
  identifier = "${local.name}-mysql"

  engine         = "mysql"
  engine_version = "8.0"

  instance_class        = var.db_instance_class
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  port     = 3306

  # RDS generates and stores the master password in Secrets Manager.
  manage_master_user_password = true

  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible = false
  multi_az            = false

  backup_retention_period = 7
  deletion_protection     = false
  skip_final_snapshot     = true

  auto_minor_version_upgrade = true
  apply_immediately          = true
}