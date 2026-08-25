terraform {
  required_version = ">= 1.8.0, < 2.0.0"

  backend "local" {}

  required_providers {
    vultr = {
      source  = "vultr/vultr"
      version = "2.32.0"
    }
  }
}

provider "vultr" {
  rate_limit  = 500
  retry_limit = 3
}
