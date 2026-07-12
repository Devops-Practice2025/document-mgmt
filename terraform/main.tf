terraform {

required_providers {
    aws = {
    source = "hashicorp/aws"
    version = "~>5.0"
}
}

backend "s3" {
  name = "bankdocs-terraform-state-techkarthi"
  region = "us-east-1"
  key = "terraform.tfstate"
  dynamodb_table = "bankdocs-terraform-state-lock-techkarthi"
}   

}