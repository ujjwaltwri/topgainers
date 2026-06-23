const fs = require('fs');

let stocks = [
  {"ticker":"BBCA.JK","pct_change":-20.33,"market_cap":752616984281088},
  {"ticker":"BBRI.JK","pct_change":-14.72,"market_cap":438173033299968},
  {"ticker":"BYAN.JK","pct_change":-24.80,"market_cap":396666670678016},
  {"ticker":"BMRI.JK","pct_change":-9.39,"market_cap":384533320957952},
  {"ticker":"TLKM.JK","pct_change":-20.83,"market_cap":250696788082688}
];

const width = 1000;
const height = 500;

const totalMcap = stocks.reduce((sum, s) => sum + s.market_cap, 0);
const totalArea = width * height;

stocks.forEach(s => {
  s._area = (s.market_cap / totalMcap) * totalArea;
});

let rects = [];

function divide(items, x, y, w, h, isVertical) {
  if (items.length === 0) return;
  if (items.length === 1) {
    rects.push({ stock: items[0], x, y, w, h });
    return;
  }
  
  const targetArea = items.reduce((s, it) => s + it._area, 0) / 2;
  let sum = 0;
  let splitIdx = 0;
  for (let i = 0; i < items.length; i++) {
    sum += items[i]._area;
    if (sum >= targetArea) {
      splitIdx = i;
      break;
    }
  }
  if (splitIdx === 0) splitIdx = 1;
  if (splitIdx === items.length) splitIdx = items.length - 1;
  
  const leftItems = items.slice(0, splitIdx);
  const rightItems = items.slice(splitIdx);
  
  const leftArea = leftItems.reduce((s, it) => s + it._area, 0);
  const rightArea = rightItems.reduce((s, it) => s + it._area, 0);
  const ratio = leftArea / (leftArea + rightArea);
  
  if (isVertical) {
    const leftW = w * ratio;
    divide(leftItems, x, y, leftW, h, false);
    divide(rightItems, x + leftW, y, w - leftW, h, false);
  } else {
    const topH = h * ratio;
    divide(leftItems, x, y, w, topH, true);
    divide(rightItems, x, y + topH, w, h - topH, true);
  }
}

divide(stocks, 0, 0, width, height, width > height);
console.log(rects);
