terraform {
  backend "gcs" {
    # One-time manual prerequisite (like the S3 bucket in the AWS example):
    # Create this bucket first, then set the real name here.
    bucket = "terraform-state-gradepilot-CHANGE_ME"
    prefix = "terraform/state"
  }
}

