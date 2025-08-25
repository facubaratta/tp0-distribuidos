#!/usr/bin/env bash
set -euo pipefail

MSG="echo-test-$(date +%s%N)"

RESPONSE=$(docker run --rm --network=tp0_testing_net alpine /bin/sh -c "echo '$MSG' | nc server 12345")

if [ "$RESPONSE" == "$MSG" ]; then
  echo "action: test_echo_server | result: success"
else
  echo "action: test_echo_server | result: fail"
fi

exit 0