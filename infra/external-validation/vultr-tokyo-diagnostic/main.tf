locals {
  region      = "nrt"
  worker_plan = "vhp-4c-8gb-amd"
  backup_plan = "vhp-2c-4gb-amd"
  labels = [
    "routemind",
    "r4-vke-connectivity-diagnostic",
    var.execution_id,
    "expires-${replace(replace(var.expires_at, ":", ""), "-", "")}",
  ]
  operator_network = split("/", var.operator_cidr)[0]
}

resource "vultr_firewall_group" "recovery" {
  description = "RouteMind ${var.execution_id} diagnostic recovery boundary"
}

resource "vultr_firewall_rule" "recovery_ssh" {
  firewall_group_id = vultr_firewall_group.recovery.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = local.operator_network
  subnet_size       = 32
  port              = "22"
  notes             = "Temporary diagnostic observer SSH for ${var.execution_id}"
}

resource "vultr_instance" "recovery" {
  region            = local.region
  plan              = local.backup_plan
  os_id             = var.recovery_os_id
  label             = "${var.execution_id}-observer"
  hostname          = "r4-vke-observer"
  firewall_group_id = vultr_firewall_group.recovery.id
  ssh_key_ids       = [var.ssh_key_id]
  backups           = "disabled"
  enable_ipv6       = false
  ddos_protection   = false
  activation_email  = false
  user_scheme       = "root"
  tags              = local.labels
  user_data = base64encode(templatefile("${path.module}/cloud-init.yaml.tftpl", {
    execution_id    = var.execution_id
    source_revision = var.source_revision
    expires_at      = var.expires_at
  }))

  depends_on = [vultr_firewall_rule.recovery_ssh]
}

resource "vultr_kubernetes" "diagnostic" {
  region           = local.region
  label            = "${var.execution_id}-vke"
  version          = var.vke_version
  ha_controlplanes = true
  enable_firewall  = true

  node_pools {
    node_quantity = 1
    plan          = local.worker_plan
    label         = "${var.execution_id}-worker"
    auto_scaler   = false
    min_nodes     = 1
    max_nodes     = 1

    labels {
      key   = "routemind.io/purpose"
      value = "r4-vke-connectivity-diagnostic"
    }

    labels {
      key   = "routemind.io/execution-id"
      value = var.execution_id
    }
  }
}

resource "vultr_firewall_rule" "vke_api_operator" {
  firewall_group_id = vultr_kubernetes.diagnostic.firewall_group_id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = local.operator_network
  subnet_size       = 32
  port              = "6443"
  notes             = "Operator diagnostic VKE API observer for ${var.execution_id}"
}

resource "vultr_firewall_rule" "vke_api_recovery" {
  firewall_group_id = vultr_kubernetes.diagnostic.firewall_group_id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = vultr_instance.recovery.main_ip
  subnet_size       = 32
  port              = "6443"
  notes             = "Tokyo observer diagnostic VKE API for ${var.execution_id}"

  depends_on = [vultr_instance.recovery]
}
