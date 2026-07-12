import {test,expect} from '@playwright/test';

test('评委浏览器核心闭环',async({page})=>{
  await page.goto('/');
  await expect(page.getByText('每个结论，都能回到证据。')).toBeVisible();
  await page.getByRole('link',{name:'查看六批背景数据'}).click();
  await expect(page.getByText('第三方实验室送样检测，不等于第三方现场采样')).toBeVisible();
  await expect(page.getByText('96.17%')).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/01-background-chain.png',fullPage:true});
  await page.getByRole('link',{name:'质量'}).click();
  await page.getByRole('button',{name:'运行质量检查'}).click();
  await expect(page.getByText('送样链条信息不完整')).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/02-quality-findings.png',fullPage:true});
  await page.getByRole('link',{name:'MRV'}).click();
  await expect(page.getByText('当前不能确认减排结论')).toBeVisible();
  await page.getByRole('link',{name:'主张门控'}).click();
  await page.getByRole('button',{name:'检查表述'}).click();
  await expect(page.getByText('该表述已拦截')).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/03-claim-block.png',fullPage:true});
  await page.getByRole('link',{name:'关于'}).click();
  await page.getByRole('link',{name:'生成演示证书'}).click();
  await page.getByRole('button',{name:'生成证书'}).click();
  await page.getByRole('button',{name:'验证完整性'}).click();
  await expect(page.getByText('输入与结果哈希匹配')).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/04-certificate-valid.png',fullPage:true});
});
