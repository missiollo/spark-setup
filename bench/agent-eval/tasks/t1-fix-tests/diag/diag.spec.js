const { test } = require('@playwright/test');
const URL = 'file://' + __dirname + '/../minesweeper.html';
async function setup(page, rows, cols, mines) {
  await page.goto(URL);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.locator('#rows').fill(String(rows));
  await page.locator('#cols').fill(String(cols));
  await page.locator('#mines').fill(String(mines));
  await page.locator('#newGame').click();
}
const st = (page) => page.evaluate(() => ({
  over: game.gameOver, win: game.checkWin(), mines: game.totalMines,
  stateRevealed: game.grid.flat().filter(c => c.revealed).length,
  domRevealed: document.querySelectorAll('#board .cell.revealed').length,
  timer: document.getElementById('timer').textContent,
}));
test('D1 5x5 24 mines, first click center', async ({ page }) => {
  await setup(page, 5, 5, 24);
  await page.locator('[data-r="2"][data-c="2"]').click();
  await page.waitForTimeout(700);
  const s = await st(page);
  s.overlay = await page.locator('.overlay-box h2').textContent().catch(() => null);
  console.log('D1', JSON.stringify(s));
});
test('D2 frequencies', async ({ page }) => {
  test.setTimeout(300000);
  const cases = [
    ['5x5/1 win on first click', 5, 5, 1, 2, 2, s => s.over && s.win],
    ['9x9/24 (0,0) is mine', 9, 9, 24, 4, 4, s => 'm00'],
    ['50x50/500 (0,0) is mine', 50, 50, 500, 25, 25, s => 'm00'],
    ['9x9/10 (0,0) revealed by flood', 9, 9, 10, 4, 4, s => 'r00'],
    ['9x9/10 (8,8) is mine', 9, 9, 10, 4, 4, s => 'm88'],
  ];
  for (const [name, r, c, m, fr, fc, pred] of cases) {
    let hit = 0, dombug = 0; const N = 30;
    for (let i = 0; i < N; i++) {
      await setup(page, r, c, m);
      await page.locator(`[data-r="${fr}"][data-c="${fc}"]`).click();
      const s = await st(page);
      const g = await page.evaluate(() => ({ m00: game.grid[0][0].mine, r00: game.grid[0][0].revealed, m88: game.grid[8] && game.grid[8][8].mine }));
      const p = pred(s);
      if (typeof p === 'string' ? g[p] : p) hit++;
      if (s.domRevealed !== s.stateRevealed) dombug++;
    }
    console.log('D2', name, `${hit}/${N}`, 'DOM≠stan:', `${dombug}/${N}`);
  }
});
test('D3 50x50 layout', async ({ page }) => {
  await setup(page, 50, 50, 500);
  const b = await page.evaluate(() => { const r = document.getElementById('board').getBoundingClientRect(); return { left: r.left, width: r.width, vw: innerWidth, scrollX: document.documentElement.scrollWidth }; });
  console.log('D3', JSON.stringify(b));
});
test('D4 loss via flood after win-state, chord DOM', async ({ page }) => {
  let win = 0, loss = 0, wins_with_dom_hidden = 0;
  for (let i = 0; i < 20; i++) {
    await setup(page, 5, 5, 1);
    await page.locator('[data-r="2"][data-c="2"]').click();
    const s = await page.evaluate(() => {
      const hiddenSafeRevealed = game.grid.flat().map((c, i) => [c, document.querySelectorAll('#board .cell')[i]]).filter(([c, el]) => !c.mine && c.revealed && el.classList.contains('hidden')).length;
      return { over: game.gameOver, win: game.checkWin(), hiddenSafeRevealed };
    });
    if (s.over && s.win) { win++; if (s.hiddenSafeRevealed > 0) wins_with_dom_hidden++; }
  }
  console.log('D4 first-click wins', win, 'of 20; of those with revealed safe cells drawn as hidden:', wins_with_dom_hidden);
});
test('D5 replay of win test loop', async ({ page }) => {
  test.setTimeout(120000);
  const outcomes = {};
  for (let i = 0; i < 10; i++) {
    await setup(page, 5, 5, 1);
    await page.locator('[data-r="2"][data-c="2"]').click();
    await page.waitForTimeout(200);
    let res = 'win-after-loop';
    const firstWin = await page.evaluate(() => game.gameOver);
    outer: for (let r = 0; r < 5; r++) for (let c = 0; c < 5; c++) {
      const cell = page.locator(`[data-r="${r}"][data-c="${c}"]`);
      if (await cell.evaluate(el => el.classList.contains('revealed'))) continue;
      try { await cell.click({ timeout: 1500 }); } catch (e) {
        res = (firstWin ? 'first-click-win, ' : '') + 'click blocked: ' + (/intercepts pointer events/.test(e.message) ? 'overlay intercepts' : e.message.split('\n')[0]); break outer;
      }
      await page.waitForTimeout(100);
      const s = await page.evaluate(() => ({ over: game.gameOver, win: game.checkWin() }));
      if (s.over && !s.win) { res = 'clicked the mine → loss'; break outer; }
    }
    outcomes[res] = (outcomes[res] || 0) + 1;
  }
  console.log('D5', JSON.stringify(outcomes));
});
