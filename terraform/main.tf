terraform {

required_providers {
  aws = {
    source = "hashicorp"
  }
}

  
}


  backend "s3" {
    key = "bankdocs-terraform-state-techkarthi"

    
  }
}