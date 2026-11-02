FROM node:22-bookworm-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
COPY docker-entrypoint.sh /usr/local/bin/frontend-entrypoint.sh
RUN chmod +x /usr/local/bin/frontend-entrypoint.sh \
    && chown -R node:node /app
USER node
EXPOSE 5173
ENTRYPOINT ["/usr/local/bin/frontend-entrypoint.sh"]
