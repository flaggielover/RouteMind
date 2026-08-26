variable "execution_id" {
  description = "Unique bounded diagnostic execution identity."
  type        = string

  validation {
    condition     = can(regex("^r4-diag-[0-9]{8}t[0-9]{6}z-[0-9a-f]{7,12}$", var.execution_id))
    error_message = "execution_id must match the bounded R4 diagnostic format."
  }
}

variable "source_revision" {
  description = "Exact RouteMind Git revision validated by this diagnostic."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.source_revision))
    error_message = "source_revision must be a full lowercase Git SHA."
  }
}

variable "expires_at" {
  description = "UTC resource-expiry label, at most two hours after creation."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", var.expires_at))
    error_message = "expires_at must be an RFC3339 UTC timestamp without fractional seconds."
  }
}

variable "vke_version" {
  description = "Authenticated-preflight-selected supported VKE version."
  type        = string

  validation {
    condition     = can(regex("^v[0-9]+\\.[0-9]+\\.[0-9]+\\+[0-9]+$", var.vke_version))
    error_message = "vke_version must be an exact Vultr VKE release identity."
  }
}

variable "recovery_os_id" {
  description = "Authenticated-preflight-selected Ubuntu 24.04 x64 OS identity."
  type        = number

  validation {
    condition     = var.recovery_os_id > 0 && floor(var.recovery_os_id) == var.recovery_os_id
    error_message = "recovery_os_id must be a positive integer."
  }
}

variable "ssh_key_id" {
  description = "Existing Vultr public SSH key identity."
  type        = string

  validation {
    condition     = length(trimspace(var.ssh_key_id)) >= 8
    error_message = "ssh_key_id must identify an existing Vultr SSH public key."
  }
}

variable "operator_cidr" {
  description = "Single operator IPv4 /32 used for SSH and VKE API diagnostics."
  type        = string

  validation {
    condition     = can(cidrhost(var.operator_cidr, 0)) && !strcontains(var.operator_cidr, ":") && split("/", var.operator_cidr)[1] == "32"
    error_message = "operator_cidr must be one operator IPv4 /32 CIDR."
  }
}
