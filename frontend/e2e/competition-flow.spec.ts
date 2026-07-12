import {expect,test} from '@playwright/test';

test('真实PostgreSQL与API比赛闭环',async({page,request})=>{
  const dashboard=await request.get('http://127.0.0.1:8000/api/v1/dashboard');
  expect(dashboard.ok()).toBeTruthy();
  expect(await dashboard.json()).toMatchObject({project_count:1,batch_count:1,sample_count:12,measurement_count:36});

  await page.goto('/');
  await expect(page.getByText('12/36')).toBeVisible();
  await page.getByRole('link',{name:'查看数据库批次'}).click();
  await page.getByRole('link',{name:'打开批次'}).click();
  await expect(page.getByText('第三方实验室送样检测，不等于第三方现场采样')).toBeVisible();
  await expect(page.getByText('96.17%')).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/v02-01-real-batch.png',fullPage:true});

  await page.getByRole('link',{name:'质量'}).click();
  await page.getByLabel('质量扫描批次').selectOption({index:1});
  await page.getByRole('button',{name:'运行质量检查'}).click();
  await expect(page.getByText(/第三方实验室送样检测缺少/).first()).toBeVisible();

  const mrv=await request.post('http://127.0.0.1:8000/api/v1/mrv/runs',{data:{activities:[
    {scenario:'baseline',name:'基准电力',factor_activity:'electricity',amount_low:1,amount_base:2,amount_high:3,unit:'kWh',source:'演示表',data_grade:'reported'},
    {scenario:'project',name:'项目电力',factor_activity:'electricity',amount_low:.5,amount_base:1,amount_high:1.5,unit:'kWh',source:'演示表',data_grade:'reported'},
  ],n2o_addressed:false,equal_effluent_goal_confirmed:false}});
  expect(mrv.ok()).toBeTruthy();
  await page.getByRole('link',{name:'MRV'}).click();
  await expect(page.getByText('INDETERMINATE')).toBeVisible();

  await page.getByRole('link',{name:'主张门控'}).click();
  await page.getByRole('button',{name:'检查表述'}).click();
  await expect(page.getByText('该表述已拦截')).toBeVisible();
  await expect(page.getByText(/组合改写/)).toBeVisible();

  await page.getByRole('link',{name:'关于'}).click();
  await page.getByRole('link',{name:'生成数据库证书'}).click();
  await page.getByRole('button',{name:'从数据库批次生成证书'}).click();
  await expect(page.getByText(/已加载manifest/)).toBeVisible();
  await page.getByRole('button',{name:'验证完整性'}).click();
  await expect(page.getByText('输入与结果哈希匹配')).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/v02-02-manifest-valid.png',fullPage:true});
});

test('证书后端不可用时只显示无法验证',async({page})=>{
  await page.route('**/api/v1/certificates/**/verify',route=>route.abort('connectionfailed'));
  await page.goto('/verify/backend-offline');
  await page.getByRole('button',{name:'验证完整性'}).click();
  await expect(page.getByRole('alert')).toContainText('无法验证');
  await expect(page.getByText('输入与结果哈希匹配')).toHaveCount(0);
  await expect(page.getByText('验证成功')).toHaveCount(0);
});
