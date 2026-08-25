locals {
  region      = "nrt"
  worker_plan = "vhp-4c-8gb-amd"
  backup_plan = "vhp-2c-4gb-amd"
  labels = [
    "routemind",
    "r4-external-validation",
    var.execution_id,
    "expires-${replace(replace(var.expires_at, ":", ""), "-", "")}",
  ]
  operator_network      = split("/", var.operator_cidr)[0]
  operator_network_bits = tonumber(split("/", var.operator_cidr)[1])
}

resource "vultr_firewall_group" "recovery" {
  description = "RouteMind ${var.execution_id} temporary recovery SSH boundary"
}

resource "vultr_firewall_rule" "recovery_ssh" {
  firewall_group_id = vultr_firewall_group.recovery.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = local.operator_network
  subnet_size       = local.operator_network_bits
  port              = "22"
  notes             = "Temporary operator SSH for ${var.execution_id}"
}

resource "vultr_instance" "recovery" {
  region            = local.region
  plan              = local.backup_plan
  os_id             = var.recovery_os_id
  label             = "${var.execution_id}-recovery"
  hostname          = "r4-recovery"
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

resource "vultr_kubernetes" "validation" {
  region           = local.region
  label            = "${var.execution_id}-vke"
  version          = var.vke_version
  ha_controlplanes = true
  enable_firewall  = true

  node_pools {
    node_quantity = 3
    plan          = local.worker_plan
    label         = "${var.execution_id}-workers"
    auto_scaler   = false
    min_nodes     = 3
    max_nodes     = 3

    labels {
      key   = "routemind.io/purpose"
      value = "r4-external-validation"
    }

    labels {
      key   = "routemind.io/execution-id"
      value = var.execution_id
    }
  }
}
