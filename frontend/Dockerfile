# 第一阶段：构建 (Build Stage)
FROM node:22-alpine as builder

WORKDIR /app

COPY package*.json ./

# --- 新增下面这一行 ---
# 设置 npm 淘宝镜像源 (或使用其他国内源)
RUN npm config set registry https://registry.npmmirror.com

RUN npm install

COPY . .
RUN npm run build

# 第二阶段保持不变 ...
FROM nginx:alpine
# ...
# 1. 移除 Nginx 默认的 html 文件
RUN rm -rf /usr/share/nginx/html/*

# 2. 从构建阶段复制生成的 dist 目录到 Nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 3. (可选) 如果你的 nginx.conf 需要被拷入镜像，可以在这里 COPY
# 但为了配置灵活，我们在 docker-compose 里通过挂载覆盖它

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
