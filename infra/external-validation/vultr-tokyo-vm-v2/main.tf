locals {
  region        = "nrt"
  operator_ipv4 = split("/", var.operator_cidr)[0]
  tags = [
    "routemind",
    "r4-vm-external-validation-v2",
    var.execution_id,
    "expires-at=${var.expires_at}",
  ]
}

resource "vultr_firewall_group" "validation" {
  description = "RouteMind ${var.execution_id} exact no-VPC VM validation ingress"
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

resource "vultr_instance" "primary" {
  plan              = "vc2-8c-32gb"
  region            = local.region
  os_id             = var.ubuntu_os_id
  label             = var.execution_id
  hostname          = "routemind-r4-primary"
  tags              = concat(local.tags, ["role=primary-validation"])
  ssh_key_ids       = [var.ssh_key_id]
  firewall_group_id = vultr_firewall_group.validation.id
  vpc_ids           = []
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
  vpc_ids           = []
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

# The recovery address is provider-assigned. Terraform cannot add this rule
# until the recovery identity exists, so the source remains one exact /32.
resource "vultr_firewall_rule" "recovery_to_primary_ssh" {
  firewall_group_id = vultr_firewall_group.validation.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = vultr_instance.recovery.main_ip
  subnet_size       = 32
  port              = "22"
  notes             = "Recovery VM SSH /32 for encrypted transfer in ${var.execution_id}"
}
