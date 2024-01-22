#!/bin/bash
set -euo pipefail
trap "echo 'error: Script failed: see failed command above'" ERR

cupsctl WebInterface=yes
