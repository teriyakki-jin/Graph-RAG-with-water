"""Playwright로 Velog 포스팅용 스크린샷 4장 자동 촬영."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT  = Path(__file__).parent.parent
BASE = "http://localhost:3000"

QUERIES = {
    "screenshot_query.png":    "탁도 기준은 얼마이고 초과 시 처분은?",
    "screenshot_multihop.png": "낙동강 페놀 사고 이후 도입된 소독 방식과 그 부산물 기준은?",
}


async def submit_and_wait(page, question: str, wait_sec: int = 40):
    """질문 입력 → 전송 → 답변 완료 대기."""
    await page.wait_for_selector("textarea:not([disabled])", timeout=10000)
    box = page.locator("textarea").first
    await box.click()
    await box.fill(question)
    await box.press("Enter")
    # textarea가 다시 활성화(=응답 완료)될 때까지 대기
    await page.wait_for_selector("textarea:not([disabled])", timeout=wait_sec * 1000)
    await asyncio.sleep(1)  # UI 렌더링 여유


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        # ── ① 메인 화면 ────────────────────────────────
        print("① 메인 화면...")
        await page.goto(BASE, wait_until="networkidle")
        await asyncio.sleep(5)  # D3 렌더링 대기
        await page.screenshot(path=str(OUT / "screenshot_main.png"))
        print("   → screenshot_main.png")

        # ── ② 단순 질의 ────────────────────────────────
        print("② 단순 질의...")
        await submit_and_wait(page, QUERIES["screenshot_query.png"], wait_sec=60)
        await page.screenshot(path=str(OUT / "screenshot_query.png"))
        print("   → screenshot_query.png")

        # ── ③ 노드 클릭 ────────────────────────────────
        print("③ 노드 클릭...")
        # SVG 중앙 좌표를 구해서 마우스로 직접 클릭
        svg_box = await page.locator("svg").first.bounding_box()
        if svg_box:
            cx = svg_box["x"] + svg_box["width"] * 0.45
            cy = svg_box["y"] + svg_box["height"] * 0.5
            await page.mouse.click(cx, cy)
            await asyncio.sleep(2)
        await page.screenshot(path=str(OUT / "screenshot_node.png"))
        print("   → screenshot_node.png")

        # ── ④ 멀티홉 질의 ──────────────────────────────
        print("④ 멀티홉 질의...")
        await page.goto(BASE, wait_until="networkidle")
        await asyncio.sleep(3)
        await submit_and_wait(page, QUERIES["screenshot_multihop.png"], wait_sec=90)
        await page.screenshot(path=str(OUT / "screenshot_multihop.png"))
        print("   → screenshot_multihop.png")

        await browser.close()
        print("\n✓ 스크린샷 4장 완료")


if __name__ == "__main__":
    asyncio.run(main())
