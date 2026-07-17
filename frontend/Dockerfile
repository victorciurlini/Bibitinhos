FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# VITE_WS_URL e resolvida em build time (Vite injeta no bundle) — por isso ARG, nao env de runtime.
ARG VITE_WS_URL=ws://localhost:8001/ws
ENV VITE_WS_URL=$VITE_WS_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
