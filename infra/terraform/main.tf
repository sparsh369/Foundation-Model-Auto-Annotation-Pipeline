###############################################################################
# Cloud-agnostic skeleton. Select a provider module via `var.cloud`.
# Provisions: managed K8s, managed Postgres, managed Redis, an object bucket,
# and a GPU node pool. Concrete provider blocks live in ./modules/<cloud>.
###############################################################################

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws   = { source = "hashicorp/aws", version = "~> 5.0" }
    google = { source = "hashicorp/google", version = "~> 5.0" }
    azurerm = { source = "hashicorp/azurerm", version = "~> 3.0" }
  }
  backend "s3" {} # configure per-environment via -backend-config
}

variable "cloud" {
  type        = string
  description = "aws | gcp | azure"
}
variable "region" { type = string }
variable "environment" {
  type    = string
  default = "production"
}
variable "gpu_node_type" {
  type    = string
  default = "g5.xlarge" # AWS A10G; override per cloud
}
variable "gpu_min_nodes" {
  type    = number
  default = 0
}
variable "gpu_max_nodes" {
  type    = number
  default = 20
}

module "platform" {
  source         = "./modules/${var.cloud}"
  region         = var.region
  environment    = var.environment
  gpu_node_type  = var.gpu_node_type
  gpu_min_nodes  = var.gpu_min_nodes
  gpu_max_nodes  = var.gpu_max_nodes
  object_bucket  = "annotations-${var.environment}"
}

output "kubeconfig" {
  value     = module.platform.kubeconfig
  sensitive = true
}
output "postgres_host" { value = module.platform.postgres_host }
output "redis_host" { value = module.platform.redis_host }
output "object_bucket" { value = module.platform.object_bucket }
