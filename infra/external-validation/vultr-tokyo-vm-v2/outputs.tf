output "resource_identity" {
  value = {
    execution_id     = var.execution_id
    region           = local.region
    vpc_mode         = "NONE"
    vpc_create_count = 0
    firewall = {
      id                       = vultr_firewall_group.validation.id
      operator_ssh_rule        = vultr_firewall_rule.operator_ssh.id
      recovery_to_primary_rule = vultr_firewall_rule.recovery_to_primary_ssh.id
      recovery_source_ipv4     = vultr_instance.recovery.main_ip
    }
    primary = {
      id        = vultr_instance.primary.id
      plan      = vultr_instance.primary.plan
      region    = vultr_instance.primary.region
      public_ip = vultr_instance.primary.main_ip
    }
    recovery = {
      id        = vultr_instance.recovery.id
      plan      = vultr_instance.recovery.plan
      region    = vultr_instance.recovery.region
      public_ip = vultr_instance.recovery.main_ip
    }
  }
}
