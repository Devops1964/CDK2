FROM node:10

WORKDIR /usr/src/nodeapp

COPY . .

# build npm dependencies
RUN npm install

EXPOSE 8083

CMD ["node", "index.js"]
