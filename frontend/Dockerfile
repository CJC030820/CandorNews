# Build stage
FROM node:18-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# API address baked into the build. Default: local backend on port 8080.
# Production passes an empty value so the browser calls the same site (/api/...).
ARG REACT_APP_API_URL=http://localhost:8080
ENV REACT_APP_API_URL=$REACT_APP_API_URL
RUN npm run build

# Production stage
FROM nginx:alpine
# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf
# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy build output
COPY --from=build /app/build /usr/share/nginx/html

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD wget -q -O - http://127.0.0.1:80 || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
