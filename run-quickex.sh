#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export CONFIG_PROFILE=quickex
exec ./run.sh
