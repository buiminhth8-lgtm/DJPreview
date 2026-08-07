import { expect, test } from "@playwright/test";

/**
 * T33-UI1-Fix1：验证原生 select 深色主题可读性（共享样式）。
 * 检查 /create 风格模板与 /projects 筛选下拉的 option 计算样式。
 */

test("dark theme select options are readable on /create and /projects", async ({ page }) => {
  // /create 风格模板下拉
  await page.goto("/create");
  const createSelect = page.locator("select").first();
  await expect(createSelect).toBeVisible();
  const createColors = await createSelect.evaluate((el) => {
    const sel = el as HTMLSelectElement;
    const selStyle = getComputedStyle(sel);
    const opt = sel.options[0];
    const optStyle = getComputedStyle(opt);
    return {
      selectColor: selStyle.color,
      selectBg: selStyle.backgroundColor,
      optionColor: optStyle.color,
      optionBg: optStyle.backgroundColor,
      colorScheme: getComputedStyle(document.documentElement).colorScheme,
    };
  });
  // 浅色文字 + 深色背景
  expect(createColors.optionColor).not.toBe("rgb(255, 255, 255)");
  expect(createColors.optionColor).not.toBe("rgb(0, 0, 0)");
  expect(createColors.optionBg).not.toBe("rgb(255, 255, 255)");
  expect(createColors.colorScheme).toBe("dark");

  // /projects 筛选下拉
  await page.goto("/projects");
  const filterSelect = page.locator("select").first();
  await expect(filterSelect).toBeVisible();
  const filterColors = await filterSelect.evaluate((el) => {
    const sel = el as HTMLSelectElement;
    const opt = sel.options[0];
    return {
      selectColor: getComputedStyle(sel).color,
      optionColor: getComputedStyle(opt).color,
      optionBg: getComputedStyle(opt).backgroundColor,
    };
  });
  expect(filterColors.optionColor).not.toBe("rgb(255, 255, 255)");
  expect(filterColors.optionBg).not.toBe("rgb(255, 255, 255)");
});
