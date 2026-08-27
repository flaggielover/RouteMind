output "resource_identity" {
  value = {
    execution_id = var.execution_id
    region       = local.region
    plan         = local.plan
    os_id        = local.ubuntu_24_04_x64_os_id
    username     = local.expected_ssh_username
    firewall = {
      id                = vultr_firewall_group.diagnostic.id
      operator_ssh_rule = vultr_firewall_rule.operator_ssh.id
    }
    diagnostic = {
      id        = vultr_instance.diagnostic.id
      public_ip = vultr_instance.diagnostic.main_ip
    }
  }
}
