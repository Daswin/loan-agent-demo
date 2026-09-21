#!/bin/sh
set -eu

envsubst '${LOAN_API_BASE}' \
  < /usr/share/nginx/html/application/config.template.js \
  > /usr/share/nginx/html/application/config.js

exec nginx -g 'daemon off;'
