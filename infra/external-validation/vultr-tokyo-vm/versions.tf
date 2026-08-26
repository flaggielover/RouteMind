terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    vultr = {
      source  = "vultr/vultr"
      version = "2.32.0"
    }
  }
}

provider "vultr" {}
