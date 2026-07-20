variable "aws_region" {
  default = "us-east-1"
}

variable "project" {
  default = "bankdocs"
}

variable "instance_type" {
  default = "t3.medium"
}

# RHEL 9 AMI differs per region - update if your region changes
variable "rhel_ami" {
  default = "ami-0220d79f3f480ecf5" # RHEL 9, us-east-1 (verify current AMI ID before use)
}
