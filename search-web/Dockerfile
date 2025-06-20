# "build-stage", based on Node.js, to build and compile the frontend
# pull official base image
FROM node:20-alpine AS build-stage

# set working directory
WORKDIR /app

# add `/app/node_modules/.bin` to $PATH
ENV PATH=/app/node_modules/.bin:$PATH

# install app dependencies
COPY package.json ./
COPY package-lock.json ./

RUN npm install --silent

# create and set user permissions to app folder
RUN mkdir -p node_modules/.cache && chmod -R 777 node_modules/.cache

# add app files
COPY . ./

RUN npm run build

# Stage 1, based on Nginx, to have only the compiled app, ready for production with Nginx
FROM nginx:1.25.3-alpine AS production-stage
RUN mkdir /app

# Install envsubst using alpine package manager
RUN apk add --no-cache gettext bash

# Add non-root user for better security
RUN adduser -D -u 1001 nginx-user

COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY /nginx/nginx.conf.template /etc/nginx/nginx.conf.template
COPY /nginx/env.sh /docker-entrypoint.d/env.sh

# Set up permissions
RUN chmod +x /docker-entrypoint.d/env.sh && \
    chown -R nginx-user:nginx-user /app && \
    chown -R nginx-user:nginx-user /var/cache/nginx && \
    chown -R nginx-user:nginx-user /var/log/nginx && \
    chown -R nginx-user:nginx-user /etc/nginx/conf.d && \
    chown -R nginx-user:nginx-user /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Create config.js file with proper permissions
RUN touch /usr/share/nginx/html/config.js && \
    chown nginx-user:nginx-user /usr/share/nginx/html/config.js && \
    chmod 644 /usr/share/nginx/html/config.js

# Switch to non-root user
USER nginx-user

EXPOSE 8080

CMD ["/bin/sh", "-c", "/docker-entrypoint.d/env.sh && envsubst '$$PROXY_API_URL' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf && nginx -c /tmp/nginx.conf -g 'daemon off;'"]
