# "build-stage", based on Node.js, to build and compile the frontend
# pull official base image
FROM node:18-alpine as build-stage

# set working directory
WORKDIR /app

# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH

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
FROM nginx:1.17 as production-stage
RUN mkdir /app

# Install envsubst for environment variable substitution
RUN apt-get update && apt-get install -y gettext-base

COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY /nginx/nginx.conf.template /etc/nginx/nginx.conf.template

EXPOSE 8080

# Replace environment variables in the template and start nginx
CMD ["/bin/sh", "-c", "envsubst '$$PROXY_API_URL' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;'"]
