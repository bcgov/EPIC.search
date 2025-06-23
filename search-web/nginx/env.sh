#!/bin/sh

# Debug: Print all environment variables
echo "Current environment variables:"
env

# Set default PROXY_API_URL if not provided
if [ -z "$PROXY_API_URL" ]; then
    echo "Warning: PROXY_API_URL not set, defaulting to http://localhost:3000"
    export PROXY_API_URL="http://localhost:3000"
else
    echo "PROXY_API_URL is set to: $PROXY_API_URL"
fi

# If PROXY_API_URL doesn't start with http:// or https://, add http://
if [[ $PROXY_API_URL != http://* ]] && [[ $PROXY_API_URL != https://* ]]; then
    echo "Adding http:// prefix to PROXY_API_URL"
    export PROXY_API_URL="http://$PROXY_API_URL"
fi

# Debug: Print final PROXY_API_URL
echo "Final PROXY_API_URL: $PROXY_API_URL"

# Recreate config file
rm -rf /usr/share/nginx/html/config.js
touch /usr/share/nginx/html/config.js

# Add assignment 
echo "window._env_ = {" >> /usr/share/nginx/html/config.js

# Read each line in .env file
# Each line represents key=value pairs
for line in $(env); do
  if [[ $line == VITE_* ]]; then
    # Split env variables by character `=`
    key=$(echo $line | cut -d '=' -f1)
    value=$(echo $line | cut -d '=' -f2-)
    
    # Append to config.js file
    echo "  $key: \"$value\"," >> /usr/share/nginx/html/config.js
  fi
done

echo "};" >> /usr/share/nginx/html/config.js
