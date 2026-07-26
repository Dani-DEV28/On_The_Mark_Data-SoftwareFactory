#!/usr/bin/env bash
# DEPRECATED (plan P3 #7): serial bash runner replaced by the TPM-driven
# pull model. Forwarding to orchestrate.sh.
exec "$(dirname "$0")/orchestrate.sh" "$@"
