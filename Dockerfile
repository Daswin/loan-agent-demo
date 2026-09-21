FROM node:20-alpine AS landing-builder

WORKDIR /landing
COPY landing/package*.json ./
RUN npm ci
COPY landing/ ./
RUN npm run build

FROM nginx:alpine

# 1. Delete Nginx's default welcome page to avoid conflicts
RUN rm /usr/share/nginx/html/index.html

# 2. Copy your custom port configuration override into the Nginx config folder
COPY default.conf /etc/nginx/conf.d/default.conf

# 3. Copy your live frontend files into Nginx's public web directory
COPY --from=landing-builder /landing/dist/ /usr/share/nginx/html/
RUN mkdir -p /usr/share/nginx/html/application
COPY index.html /usr/share/nginx/html/application/index.html
COPY app.js /usr/share/nginx/html/application/app.js
COPY config.js /usr/share/nginx/html/application/config.js
COPY config.template.js /usr/share/nginx/html/application/config.template.js
COPY frontend-entrypoint.sh /frontend-entrypoint.sh
RUN chmod +x /frontend-entrypoint.sh

# Expose port 8080 for Cloud Run
EXPOSE 8080

ENTRYPOINT ["/frontend-entrypoint.sh"]
