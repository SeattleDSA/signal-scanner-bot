#!/bin/bash

set -e

if signal-cli -u "$BOT_NUMBER" register 2>&1 | grep -qi 'captcha'; then
  echo "Captcha required, please visit https://signalcaptchas.org/registration/generate.html to receive a captcha token"
  read -r CAPTCHA
  signal-cli -u "$BOT_NUMBER" register --captcha "$CAPTCHA"
fi
echo "Enter the verification value sent to the primary phone"
read -r verification
if signal-cli -u "$BOT_NUMBER" verify "$verification"; then
  echo "Verification succeeded, $BOT_NUMBER can now be used"
else
  echo "Verification failed, see error output (last error code: $?)"
fi