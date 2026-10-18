# Unified RescueFlow web UI for Cloud Run (nginx on :8080).
# Build context: frontend/
#
#   docker build --build-arg VITE_API_URL=https://api.example.run.app -t foodbridge-ui .
ARG VITE_API_URL=
ARG VITE_AUTH_MODE=demo

FROM node:20-alpine AS build
ARG VITE_API_URL
ARG VITE_AUTH_MODE
ENV VITE_API_URL=${VITE_API_URL} \
    VITE_AUTH_MODE=${VITE_AUTH_MODE}

WORKDIR /build
COPY package.json package-lock.json ./
COPY shared ./shared
COPY index.html vite.config.ts tsconfig.json ./
COPY src ./src
RUN npm ci
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
