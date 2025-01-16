const http = require('http');

const port = 80;

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain');
  res.end('Hello aws cloud demos!!ver25');
});

server.listen(port,() => {
  console.log(`Server running at ${port}`);
});
