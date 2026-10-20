# syntax=docker/dockerfile:1

FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# 不執行套件的 install script，降低供應鏈風險
RUN npm ci --ignore-scripts
COPY . .
RUN npm run build

FROM nginx:1.30-alpine AS runtime
# 執行期可覆寫；TILE_URL 空白時前端使用 OpenStreetMap。
# DNS_RESOLVER：Docker 內建 DNS；部署到 Kubernetes 時改成叢集 DNS 的位址
ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000 \
    DNS_RESOLVER=127.0.0.11 \
    TILE_URL="" \
    TILE_ATTRIBUTION=""
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
