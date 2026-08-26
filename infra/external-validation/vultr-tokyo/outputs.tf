output "validation_inventory" {
  description = "Non-secret provider identities used by the external evidence manifest."
  value = {
    provider          = "Vultr"
    region            = "nrt"
    execution_id      = var.execution_id
    vke_id            = vultr_kubernetes.validation.id
    vke_label         = vultr_kubernetes.validation.label
    vke_endpoint      = vultr_kubernetes.validation.endpoint
    vke_ip            = vultr_kubernetes.validation.ip
    vke_version       = vultr_kubernetes.validation.version
    vke_ha            = vultr_kubernetes.validation.ha_controlplanes
    firewall_group_id = vultr_firewall_group.recovery.id
    recovery_id       = vultr_instance.recovery.id
    recovery_ip       = vultr_instance.recovery.main_ip
    recovery_plan     = vultr_instance.recovery.plan
    expires_at        = var.expires_at
    source_revision   = var.source_revision
  }
}

output "vke_kube_config" {
  description = "Sensitive base64 kubeconfig; write only to the restricted execution state directory."
  value       = vultr_kubernetes.validation.kube_config
  sensitive   = true
}
