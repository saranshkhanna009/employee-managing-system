# Build stage
FROM node:20.11.1-alpine3.19 AS builder

WORKDIR /app

# Vite embeds this value into the static bundle during the image build.
ARG VITE_API_URL
RUN test -n "$VITE_API_URL"
ENV VITE_API_URL=${VITE_API_URL}

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:1.27.0-alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config for SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --output-document=/dev/null http://localhost:5173/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
