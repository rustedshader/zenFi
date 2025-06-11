# Build stage
FROM node:18-alpine AS builder

# Install Python3 and build tools for Alpine
RUN apk add --no-cache python3 make g++

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm install --force

# Copy the rest of the application
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine AS runner

WORKDIR /app

# Copy only the standalone output and public folder
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static

# (Optional) Copy package.json if needed for runtime scripts
COPY --from=builder /app/package.json ./package.json

# Start the standalone server
CMD ["node", "server.js"]