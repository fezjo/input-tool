const fs = require('fs');

const line = fs.readFileSync(0, 'utf8').trim();
if (line) {
  console.log(Number(line));
}
