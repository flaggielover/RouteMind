locals {
  region                     = "nrt"
  plan                       = "vc2-1c-1gb"
  ubuntu_24_04_x64_os_id     = 2284
  expected_ssh_username      = "root"
  expected_public_key_sha256 = "SHA256:JHiQkjaVyp5ft91S12iyyCbDB6PCAGhDqYTVnMJAUeI"
  operator_ipv4              = split("/", var.operator_cidr)[0]
  tags = [
    "routemind",
    "r4-vm-ssh-readiness-v1",
    var.execution_id,
    "expires-at=${var.expires_at}",
  ]
}

resource "vultr_firewall_group" "diagnostic" {
  description = "RouteMind ${var.execution_id} minimal SSH-readiness ingress"
}

resource "vultr_firewall_rule" "operator_ssh" {
  firewall_group_id = vultr_firewall_group.diagnostic.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = local.operator_ipv4
  subnet_size       = 32
  port              = "22"
  notes             = "Operator SSH /32 for ${var.execution_id}"
}

resource "vultr_instance" "diagnostic" {
  plan              = local.plan
  region            = local.region
  os_id             = local.ubuntu_24_04_x64_os_id
  label             = var.execution_id
  hostname          = "routemind-r4-ssh-readiness"
  tags              = concat(local.tags, ["role=ssh-readiness-diagnostic"])
  ssh_key_ids       = [var.ssh_key_id]
  firewall_group_id = vultr_firewall_group.diagnostic.id
  vpc_ids           = []
  backups           = "disabled"
  enable_ipv6       = false
  ddos_protection   = false
  activation_email  = false
  user_scheme       = local.expected_ssh_username
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    execution_id               = var.execution_id
    expected_public_key_sha256 = local.expected_public_key_sha256
    expected_ssh_username      = local.expected_ssh_username
  })
}
