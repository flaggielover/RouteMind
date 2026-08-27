variable "execution_id" {
  type = string
  validation {
    condition     = can(regex("^r4-vm-v2-[0-9]{8}t[0-9]{6}z-[0-9a-f]{7,12}$", var.execution_id))
    error_message = "execution_id must be an exact RouteMind VM v2 validation identity."
  }
}

variable "expires_at" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", var.expires_at))
    error_message = "expires_at must be a UTC timestamp."
  }
}

variable "ubuntu_os_id" {
  type = number
  validation {
    condition     = var.ubuntu_os_id > 0
    error_message = "ubuntu_os_id must be selected by authenticated read-only preflight."
  }
}

variable "ssh_key_id" {
  type      = string
  sensitive = true
  validation {
    condition     = length(trimspace(var.ssh_key_id)) > 0
    error_message = "ssh_key_id must identify an existing provider-side public key."
  }
}

variable "operator_cidr" {
  type = string
  validation {
    condition     = can(cidrhost(var.operator_cidr, 0)) && endswith(var.operator_cidr, "/32")
    error_message = "operator_cidr must be one exact IPv4 /32."
  }
}
