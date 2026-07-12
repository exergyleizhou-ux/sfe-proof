FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 80
HEALTHCHECK CMD wget -q -O- http://127.0.0.1/ >/dev/null || exit 1
CMD ["npm", "run", "preview"]
