import React from 'react';
import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {SWRConfig} from 'swr';
import {expect, test, vi} from 'vitest';

import {BatchDetail, Batches, Claims, Dashboard, MRV, Verify} from '../src/pages/Pages';

function response(data:unknown, ok=true){return {ok,json:async()=>data} as Response}
function wrap(node:React.ReactNode, entry='/'){
  return render(<SWRConfig value={{provider:()=>new Map(),dedupingInterval:0}}><MemoryRouter initialEntries={[entry]}>{node}</MemoryRouter></SWRConfig>);
}

test('Dashboard数字来自API',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({project_count:1,batch_count:1,sample_count:12,measurement_count:36,provenance_gap_count:12,latest_mrv:null})));
  wrap(<Dashboard/>); expect(await screen.findByText('12/36')).toBeInTheDocument();
});

test('批次详情展示API送样标签与测量',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({id:7,project_id:1,batch_code:'SFE-BG',notes:'API batch',flow_m3_d:null,evidence_level:'background',calculations:{TN_mg_L:{influent_mean:20,effluent_mean:1,concentration_reduction_pct:95,metric_label:'浓度削减',qualifier_note:null}},samples:[{id:1,sample_code:'S-1',sample_role:'influent',sampled_at:'2023-11-08T00:00:00',provenance_type:'submitted_to_third_party_lab',sampler_name:null,sampling_location:null,laboratory_name:'Lab',provenance_warning:'第三方实验室送样检测，不等于第三方现场采样',measurements:[{id:1,parameter_code:'TN_mg_L',value:20,unit:'mg/L',qualifier:'equal',detection_limit:null,data_grade:'reported'}]}]})));
  wrap(<Routes><Route path="/batches/:id" element={<BatchDetail/>}/></Routes>,'/batches/7');
  expect(await screen.findByText('第三方实验室送样检测，不等于第三方现场采样')).toBeInTheDocument(); expect(screen.getByText('20 mg/L')).toBeInTheDocument();
});

test('MRV不完整状态来自API',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response([{id:1,functional_unit:'处理1 m³',unit_intensity:'gCO2e/m3',baseline_emissions:2,project_emissions:1,difference:1,conclusion_status:'indeterminate',missing_items:['N₂O'],sensitivity:{low:.8,base:1,high:1.2},contributors:[]}])));
  wrap(<MRV/>); expect(await screen.findByText('INDETERMINATE')).toBeInTheDocument(); expect(screen.getByText('N₂O')).toBeInTheDocument();
});

test('Claim Gate后端失败不显示模拟结论',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline')));wrap(<Claims/>);fireEvent.click(screen.getByText('检查表述'));await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('无法检查'));expect(screen.queryByText('该表述已拦截')).not.toBeInTheDocument();
});

test('证书后端失败显示无法验证且绝不成功',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline')));wrap(<Routes><Route path="/verify/:certificateId" element={<Verify/>}/></Routes>,'/verify/demo');fireEvent.click(screen.getByText('验证完整性'));await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('无法验证'));expect(screen.queryByText('输入与结果哈希匹配')).not.toBeInTheDocument();
});

test('证书API返回invalid时显示篡改',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({valid:false})));wrap(<Routes><Route path="/verify/:certificateId" element={<Verify/>}/></Routes>,'/verify/tampered');fireEvent.click(screen.getByText('验证完整性'));expect(await screen.findByText('证书绑定已被修改')).toBeInTheDocument();
});

test('CSV类型错误不调用API',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response([{id:1,batch_code:'B-1',evidence_level:'student',sample_count:0,notes:''}])));wrap(<Batches/>);await screen.findByRole('heading',{name:'B-1'});fireEvent.change(screen.getByLabelText('CSV导入'),{target:{files:[new File(['bad'],'data.txt',{type:'text/plain'})]}});expect(screen.getByRole('alert')).toHaveTextContent('仅支持CSV文件');
});
