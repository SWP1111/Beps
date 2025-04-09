#!/bin/bash

# Start the Express server using PM2
pm2 start /home/user_ccp/sample/beps_cdn_test/ecosystem.config.js

# Start the Nginx server
sudo nginx -c /home/user_ccp/sample/beps_cdn_test/nginx.conf

# Wait for all background processes to finish
wait
