output "diagnostic_inventory" {
  description = "Non-secret provider identities used by the connectivity diagnostic."
  value = {
    provider                   = "Vultr"
    region                     = "nrt"
    execution_id               = var.execution_id
    vke_id                     = vultr_kubernetes.diagnostic.id
    vke_label                  = vultr_kubernetes.diagnostic.label
    vke_endpoint               = vultr_kubernetes.diagnostic.endpoint
    vke_ip                     = vultr_kubernetes.diagnostic.ip
    vke_firewall_group_id      = vultr_kubernetes.diagnostic.firewall_group_id
    vke_api_operator_rule_id   = vultr_firewall_rule.vke_api_operator.id
    vke_api_recovery_rule_id   = vultr_firewall_rule.vke_api_recovery.id
    vke_version                = vultr_kubernetes.diagnostic.version
    recovery_firewall_group_id = vultr_firewall_group.recovery.id
    recovery_id                = vultr_instance.recovery.id
    recovery_ip                = vultr_instance.recovery.main_ip
    recovery_plan              = vultr_instance.recovery.plan
    expires_at                 = var.expires_at
    source_revision            = var.source_revision
  }
}

output "vke_kube_config" {
  description = "Sensitive kubeconfig retained only in the restricted execution directory."
  value       = vultr_kubernetes.diagnostic.kube_config
  sensitive   = true
}
