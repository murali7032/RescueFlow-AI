# Build any of the three Vite apps for Cloud Run (nginx on :8080).
# Context must be the frontend/ directory.
#
#   docker build --build-arg APP=donor --build-arg VITE_API_URL=https://... -t donor-ui .
ARG APP=donor
ARG VITE_API_URL=
ARG VITE_AUTH_MODE=demo

FROM node:20-alpine AS build
ARG APP
ARG VITE_API_URL
ARG VITE_AUTH_MODE
ENV VITE_API_URL=${VITE_API_URL} \
    VITE_AUTH_MODE=${VITE_AUTH_MODE}

WORKDIR /build
COPY shared ./shared
COPY ${APP}/package.json ${APP}/package-lock.json ./${APP}/
WORKDIR /build/${APP}
RUN npm ci
COPY ${APP}/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
ARG APP
COPY --from=build /build/${APP}/dist /usr/share/nginx/html
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
