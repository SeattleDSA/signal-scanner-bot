#!/bin/bash

signal-cli -u $BOT_NUMBER register
echo "Enter the verification value sent to the primary phone"
read verification
if signal-cli -u $BOT_NUMBER verify $verification; then
  echo "Verification succeeded, $BOT_NUMBER can now be used"
else
  echo "Verification failed, see error output (last error code: $?)"
fi