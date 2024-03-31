---
created_at: 2024-03-30 13:26:24.254428
layout: post.html.j2
published: true
published_at: '2024-03-30T13:31:20.882369'
tags: [docker, javascript, react, frontend]
title: Containerize react app
description: Containerize a JavaScript React app using Docker and serve it via Nginx.
---

## Docker image
```Dockerfile
FROM node:alpine as builder

WORKDIR /usr/app

COPY package.json yarn.lock /usr/app/
RUN yarn install
COPY . .

RUN yarn build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /usr/app/build /usr/share/nginx/html

CMD [ "nginx", "-g", "daemon off;" ]
```

## Nginx conf
```
# nginx.conf
server {
  listen 80;
  
  location / {
    root /usr/share/nginx/html;
    index index.html index.htm;
    try_files $uri $uri/ /index.html =404;
  }
}
```
