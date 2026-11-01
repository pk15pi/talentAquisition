#!/bin/sh
set -e
cd /app
if [ ! -x node_modules/.bin/vite ]; then
  echo "Installing frontend dependencies into the node_modules volume"
  npm ci
fi
exec npm run dev
