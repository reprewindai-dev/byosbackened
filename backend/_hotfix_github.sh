#!/bin/sh
set -e
cid=1219ce7c1716
docker exec $cid sh -lc 'if [ -f /app/.env ]; then grep -v "^GITHUB_CLIENT_ID=\|^GITHUB_CLIENT_SECRET=\|^GITHUB_REDIRECT_URI=" /app/.env > /tmp/.env.new; else : > /tmp/.env.new; fi; printf "%s\n" "GITHUB_CLIENT_ID=Ov23lijPnrtxwjtoP2vk" "GITHUB_CLIENT_SECRET=d3ed45bbaf1a81765d742508880be03dd5d7f2f1" "GITHUB_REDIRECT_URI=https://veklom.com/auth/github/callback" >> /tmp/.env.new; mv /tmp/.env.new /app/.env'
docker restart $cid >/dev/null
