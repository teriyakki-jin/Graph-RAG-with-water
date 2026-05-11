"""노드 클릭 스크린샷만 다시 촬영."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT  = Path(__file__).parent.parent
BASE = "http://localhost:3000"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        await page.goto(BASE, wait_until="networkidle")
        await asyncio.sleep(6)

        # DOM 구조 확인
        info = await page.evaluate("""() => {
            const all = document.querySelectorAll('circle');
            const inView = Array.from(all).filter(c => {
                const r = c.getBoundingClientRect();
                return r.width > 0 && r.left > 0 && r.left < 1000 && r.top > 0 && r.top < 850;
            });
            return {
                total: all.length,
                inView: inView.length,
                first: inView[0] ? (() => {
                    const r = inView[0].getBoundingClientRect();
                    return {x: r.left + r.width/2, y: r.top + r.height/2};
                })() : null
            };
        }""")
        print(f"circle 전체: {info['total']}, 뷰포트 내: {info['inView']}, 첫번째: {info['first']}")

        if info['first']:
            cx, cy = info['first']['x'], info['first']['y']
            await page.mouse.click(cx, cy)
            print(f"클릭: ({cx:.0f}, {cy:.0f})")
            await asyncio.sleep(2)
        else:
            # 강제로 중앙 부근 클릭 시도
            await page.mouse.click(500, 450)
            await asyncio.sleep(2)

        await page.screenshot(path=str(OUT / "screenshot_node.png"))
        print("screenshot_node.png 저장")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
