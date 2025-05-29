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
FROM nginx:1.24-alpine AS production-stage
RUN mkdir /app

# Install envsubst using alpine package manager
RUN apk add --no-cache gettext

# Add non-root user for better security
RUN adduser -D -u 1001 nginx-user && \
    chown -R nginx-user:nginx-user /app && \
    chown -R nginx-user:nginx-user /var/cache/nginx && \
    chown -R nginx-user:nginx-user /var/log/nginx && \
    chown -R nginx-user:nginx-user /etc/nginx/conf.d

COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY /nginx/nginx.conf.template /etc/nginx/nginx.conf.template

# Switch to non-root user
USER nginx-user

EXPOSE 8080

CMD ["/bin/sh", "-c", "envsubst '$$PROXY_API_URL' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf && nginx -c /tmp/nginx.conf -g 'daemon off;'"]
