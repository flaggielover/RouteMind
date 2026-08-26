locals {
  region        = "nrt"
  vpc_subnet    = "10.77.0.0"
  vpc_mask      = 24
  operator_ipv4 = split("/", var.operator_cidr)[0]
  tags = [
    "routemind",
    "r4-vm-external-validation",
    var.execution_id,
    "expires-at=${var.expires_at}",
  ]
}

resource "vultr_vpc" "validation" {
  description    = "RouteMind ${var.execution_id} private validation network"
  region         = local.region
  v4_subnet      = "10.77.0.0"
  v4_subnet_mask = 24
}

resource "vultr_firewall_group" "validation" {
  description = "RouteMind ${var.execution_id} exact VM validation ingress"
}

resource "vultr_firewall_rule" "operator_ssh" {
  firewall_group_id = vultr_firewall_group.validation.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = local.operator_ipv4
  subnet_size       = 32
  port              = "22"
  notes             = "Operator SSH /32 for ${var.execution_id}"
}

resource "vultr_firewall_rule" "private_recovery_ssh" {
  firewall_group_id = vultr_firewall_group.validation.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = local.vpc_subnet
  subnet_size       = local.vpc_mask
  port              = "22"
  notes             = "Private VPC recovery transfer for ${var.execution_id}"
}

resource "vultr_instance" "primary" {
  plan              = "vc2-8c-32gb"
  region            = local.region
  os_id             = var.ubuntu_os_id
  label             = var.execution_id
  hostname          = "routemind-r4-primary"
  tags              = concat(local.tags, ["role=primary-validation"])
  ssh_key_ids       = [var.ssh_key_id]
  firewall_group_id = vultr_firewall_group.validation.id
  vpc_ids           = [vultr_vpc.validation.id]
  backups           = "disabled"
  enable_ipv6       = false
  ddos_protection   = false
  activation_email  = false
  user_scheme       = "root"
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    execution_id = var.execution_id
    role         = "primary-validation"
  })
}

resource "vultr_instance" "recovery" {
  plan              = "vc2-2c-4gb"
  region            = local.region
  os_id             = var.ubuntu_os_id
  label             = var.execution_id
  hostname          = "routemind-r4-recovery"
  tags              = concat(local.tags, ["role=recovery-validation"])
  ssh_key_ids       = [var.ssh_key_id]
  firewall_group_id = vultr_firewall_group.validation.id
  vpc_ids           = [vultr_vpc.validation.id]
  backups           = "disabled"
  enable_ipv6       = false
  ddos_protection   = false
  activation_email  = false
  user_scheme       = "root"
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    execution_id = var.execution_id
    role         = "recovery-validation"
  })
}
