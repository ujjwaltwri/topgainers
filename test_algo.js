const width = 1000;
const height = 500;

let stocks = [
  {'ticker': '0001.HK', 'market_cap': 32737509882, 'pct_change': 24.6486},
  {'ticker': '0004.HK', 'market_cap': 7177580318, 'pct_change': -18.0859}
];

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
