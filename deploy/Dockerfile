# Production web image: build the SPA, then serve it with unprivileged Nginx.
# The API is not in this image. Nginx proxies /api/ and /admin/ to the backend.

FROM node:22-bookworm-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
USER root
RUN apk add --no-cache wget
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend /src/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
