# ============================================================
# Defendra.AI Frontend Dockerfile
# ============================================================
# Build with: docker build --build-arg VITE_API_URL=https://your-api.com -t defendra-frontend .
# ============================================================

# Stage 1: Build the React application
FROM node:22-alpine AS build

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --only=production=false

# Copy source files
COPY . .

# Build arguments for environment variables (embedded at build time)
ARG VITE_API_URL=http://127.0.0.1:8000
ARG VITE_WS_URL=ws://127.0.0.1:8000/ws/dashboard

# Set environment variables for Vite build
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

# Build the application
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.27-alpine

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
