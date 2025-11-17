terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "organization_name" {
  description = "Name of the organization (used for resource naming)"
  type        = string
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.organization_name))
    error_message = "Organization name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "openai_api_key" {
  description = "OpenAI API key for the organization"
  type        = string
  sensitive   = true
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit for Cloud Run instances"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Memory limit for Cloud Run instances"
  type        = string
  default     = "2Gi"
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances (0 for pay-per-use)"
  type        = number
  default     = 0
}

variable "timeout_seconds" {
  description = "Request timeout for Cloud Run"
  type        = number
  default     = 300
}

variable "enable_public_access" {
  description = "Enable public access to the Cloud Run service"
  type        = bool
  default     = true
}