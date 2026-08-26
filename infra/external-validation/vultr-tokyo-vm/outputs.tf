output "resource_identity" {
  value = {
    execution_id = var.execution_id
    region       = local.region
    vpc = {
      id   = vultr_vpc.validation.id
      cidr = "${vultr_vpc.validation.v4_subnet}/${vultr_vpc.validation.v4_subnet_mask}"
    }
    firewall = {
      id                    = vultr_firewall_group.validation.id
      operator_ssh_rule     = vultr_firewall_rule.operator_ssh.id
      private_recovery_rule = vultr_firewall_rule.private_recovery_ssh.id
    }
    primary = {
      id          = vultr_instance.primary.id
      plan        = vultr_instance.primary.plan
      region      = vultr_instance.primary.region
      public_ip   = vultr_instance.primary.main_ip
      internal_ip = vultr_instance.primary.internal_ip
    }
    recovery = {
      id          = vultr_instance.recovery.id
      plan        = vultr_instance.recovery.plan
      region      = vultr_instance.recovery.region
      public_ip   = vultr_instance.recovery.main_ip
      internal_ip = vultr_instance.recovery.internal_ip
    }
  }
}
