variable "aws_region" {
  description = "region default to us-east-1"
  default     = "us-east-1"
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "bankdocs"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR assigned to the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "db_name" {
  type    = string
  default = "bankdocs"
}

variable "db_username" {
  type    = string
  default = "bankdocsadmin"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "document_bucket_name" {
  description = "Globally unique S3 bucket name"
  type        = string
}
variable "kubernetes_version" {
  type    = string
  default = "1.35"
}
