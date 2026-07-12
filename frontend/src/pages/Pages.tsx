import React, {FormEvent, useState} from 'react';
import {Link, useLocation, useNavigate, useParams} from 'react-router-dom';
import useSWR, {mutate} from 'swr';

import {api} from '../api/client';
import {Badge, ProvenanceWarning} from '../components/Badge';

type Measurement = {id:number;parameter_code:string;value:number;unit:string;qualifier:string;detection_limit:number|null;data_grade:string};
type Sample = {id:number;sample_code:string;sample_role:string;sampled_at:string|null;provenance_type:string;sampler_name:string|null;sampling_location:string|null;laboratory_name:string|null;provenance_warning:string|null;measurements:Measurement[]};
type Reduction = {influent_mean:number;effluent_mean:number;concentration_reduction_pct:number;metric_label:string;qualifier_note:string|null};
type Batch = {id:number;project_id:number;batch_code:string;started_at:string|null;ended_at:string|null;flow_m3_d:number|null;evidence_level:string;notes:string;sample_count?:number;samples?:Sample[];calculations?:Record<string,Reduction>};
type ImportResult = {rows_received:number;accepted:number;samples_created:number;measurements_created:number;errors:{row:number;message:string}[]};
type DashboardData = {project_count:number;batch_count:number;sample_count:number;measurement_count:number;provenance_gap_count:number;latest_mrv:MRVRun|null};
type MRVRun = {id:number;functional_unit:string;unit_intensity:string;baseline_emissions:number;project_emissions:number;difference:number;conclusion_status:string;missing_items:string[];sensitivity:Record<string,{baseline:number;project:number;difference:number}>;contributors:{name:string;emissions:Record<string,number>;data_grade:string;factor_source:string}[]};
type EvidenceRecord = {id:number;name:string;status:string;file_reference:string|null;limitations:string};
type Finding = {id?:number;rule_id:string;severity:string;description:string;innocent_explanation:string;suggested_action:string;scan_run_id?:string};

const fetcher = <T,>(url:string) => api<T>(url);

function Header({eyebrow,title,sub}:{eyebrow:string;title:string;sub:string}){
  return <header><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{sub}</p></header>;
}

function RequestState({loading,error}:{loading:boolean;error:unknown}){
  if(loading) return <p role="status">正在读取数据库…</p>;
  if(error) return <p role="alert" className="error">无法读取：{error instanceof Error?error.message:'请求失败'}</p>;
  return null;
}

export function Dashboard(){
  const {data,error,isLoading}=useSWR<DashboardData>('/api/v1/dashboard',fetcher);
  if(!data) return <><Header eyebrow="COMPETITION PROTOTYPE" title="每个结论，都能回到证据。" sub="真实数据库运行概览"/><RequestState loading={isLoading} error={error}/></>;
  const latest=data.latest_mrv;
  return <><Header eyebrow="COMPETITION PROTOTYPE" title="每个结论，都能回到证据。" sub="硫铁复合深度脱氮除磷项目的运行数据、样本链、筛选级碳核算和可验证证据系统。"/><section className="metrics"><article><small>数据库项目/批次</small><b>{data.project_count}/{data.batch_count}</b><span>来自API</span></article><article><small>样本/测量</small><b>{data.sample_count}/{data.measurement_count}</b><span>数据库记录</span></article><article><small>样本链缺口</small><b>{data.provenance_gap_count}</b><span>需保留来源限定</span></article><article><small>最新 MRV</small><b>{latest?.conclusion_status??'尚未运行'}</b><span>{latest?.unit_intensity??'无结果'}</span></article></section><section className="split"><article className="panel"><h2>证据边界</h2><ProvenanceWarning/><p>页面数字由后端数据库返回；送样记录的采样人或现场地点缺失会保留为质量发现。</p><Link className="button" to="/batches">查看数据库批次</Link></article><article className="panel dark"><span className="eyebrow">REAL CHAIN</span><h2>真实前后端链路</h2><p>导入、质量扫描、MRV、主张检查与证书验证均由API产生；API失败不会显示成功状态。</p></article></section></>;
}

export function Batches(){
  const {data,error,isLoading}=useSWR<Batch[]>('/api/v1/batches',fetcher);
  const [batchId,setBatchId]=useState(''); const [uploading,setUploading]=useState(false); const [uploadError,setUploadError]=useState(''); const [result,setResult]=useState<ImportResult|null>(null);
  async function upload(file:File|undefined){
    setResult(null);setUploadError(''); if(!file) return; if(!file.name.toLowerCase().endsWith('.csv')){setUploadError('仅支持CSV文件');return}
    if(!batchId){setUploadError('请先选择目标批次');return} setUploading(true);
    try{const form=new FormData();form.append('file',file);const imported=await api<ImportResult>(`/api/v1/batches/${batchId}/import`,{method:'POST',body:form});setResult(imported);await mutate('/api/v1/batches');await mutate(`/api/v1/batches/${batchId}`);await mutate('/api/v1/dashboard')}
    catch(err){setUploadError(err instanceof Error?err.message:'导入失败')}finally{setUploading(false)}
  }
  return <><Header eyebrow="BATCH REGISTER" title="批次与样本链" sub="列表、数量与导入结果均来自数据库。"/><RequestState loading={isLoading} error={error}/>{data&&<div className="toolbar"><select aria-label="目标批次" value={batchId} onChange={e=>setBatchId(e.target.value)}><option value="">选择目标批次</option>{data.map(batch=><option key={batch.id} value={batch.id}>{batch.batch_code}</option>)}</select><label className="upload">{uploading?'正在导入…':'导入CSV'}<input aria-label="CSV导入" disabled={uploading} type="file" accept=".csv,text/csv" onChange={e=>upload(e.target.files?.[0])}/></label></div>}{uploadError&&<p role="alert" className="error">导入失败：{uploadError}</p>}{result&&<div className="panel" data-testid="import-result"><h2>导入结果</h2><p>接收 {result.rows_received} 行，成功 {result.accepted} 行；新增 {result.samples_created} 个样本、{result.measurements_created} 条测量。</p>{result.errors.map(item=><p className="error" key={`${item.row}-${item.message}`}>第 {item.row} 行：{item.message}</p>)}</div>}{data?.map(batch=><article className="panel row" key={batch.id}><div><Badge tone={batch.evidence_level==='background'?'warn':'neutral'}>{batch.evidence_level}</Badge><h2>{batch.batch_code}</h2><p>{batch.notes}</p><Link to={`/batches/${batch.id}`}>打开批次</Link></div><div><b>{batch.sample_count??0}</b><small>样本</small></div></article>)}</>;
}

export function BatchDetail(){
  const {id}=useParams(); const {data,error,isLoading}=useSWR<Batch>(id?`/api/v1/batches/${id}`:null,fetcher);
  if(!data) return <><Header eyebrow="BATCH" title="批次详情" sub="样本和测量由API读取"/><RequestState loading={isLoading} error={error}/></>;
  const reductions=data.calculations??{};
  return <><Header eyebrow={data.batch_code} title="批次样本与测量" sub={data.notes}/>{data.samples?.some(sample=>sample.provenance_warning)&&<ProvenanceWarning/>}<div className="panel"><table><thead><tr><th>采样时间</th><th>样本</th><th>角色</th><th>参数</th><th>结果</th><th>等级</th></tr></thead><tbody>{data.samples?.flatMap(sample=>sample.measurements.map(measurement=><tr key={measurement.id}><td>{sample.sampled_at?.slice(0,10)??'未记录'}</td><td>{sample.sample_code}</td><td>{sample.sample_role}</td><td>{measurement.parameter_code}</td><td>{measurement.qualifier==='less_than'?'＜':''}{measurement.value} {measurement.unit}</td><td>{measurement.data_grade}</td></tr>))}</tbody></table></div><section className="metrics three">{Object.entries(reductions).map(([parameter,value])=><article key={parameter}><small>{parameter}</small><b>{value.influent_mean} → {value.effluent_mean}</b><span>{value.metric_label} {value.concentration_reduction_pct}%</span>{value.qualifier_note&&<small>{value.qualifier_note}</small>}</article>)}<article><small>负荷削减</small><b>{data.flow_m3_d===null?'未计算':'需调用负荷API'}</b><span>{data.flow_m3_d===null?'缺少可核验流量':`${data.flow_m3_d} m³/d`}</span></article></section></>;
}

export function Quality(){
  const {data:batches}=useSWR<Batch[]>('/api/v1/batches',fetcher); const [batchId,setBatchId]=useState(''); const [findings,setFindings]=useState<Finding[]>([]); const [error,setError]=useState(''); const [running,setRunning]=useState(false);
  async function run(){if(!batchId){setError('请选择批次');return}setError('');setRunning(true);try{const response=await api<{findings:Finding[]}>(`/api/v1/quality/scan`,{method:'POST',body:JSON.stringify({batch_id:Number(batchId)})});setFindings(response.findings)}catch(err){setFindings([]);setError(err instanceof Error?err.message:'扫描失败')}finally{setRunning(false)}}
  return <><Header eyebrow="QUALITY REVIEW" title="数据质量预警" sub="扫描指定数据库批次；发现按批次与扫描运行隔离。"/><select aria-label="质量扫描批次" value={batchId} onChange={e=>setBatchId(e.target.value)}><option value="">选择批次</option>{batches?.map(batch=><option value={batch.id} key={batch.id}>{batch.batch_code}</option>)}</select> <button className="button" disabled={running} onClick={run}>{running?'扫描中…':'运行质量检查'}</button>{error&&<p role="alert" className="error">无法扫描：{error}</p>}<div data-testid="quality-results">{findings.map((finding,index)=><article className="finding" key={finding.id??`${finding.rule_id}-${index}`}><Badge tone="warn">{finding.rule_id}</Badge><h2>{finding.description}</h2><small>可能的正常解释：{finding.innocent_explanation}</small><p>建议：{finding.suggested_action}</p></article>)}</div>{!error&&!findings.length&&<p className="empty">尚无本批次扫描结果。</p>}</>;
}

export function MRV(){
  const {data,error,isLoading}=useSWR<MRVRun[]>('/api/v1/mrv/runs',fetcher); const run=data?.[0];
  if(!run) return <><Header eyebrow="SCREENING MRV" title="筛选级碳核算" sub="结果由后端因子注册表与活动数据计算。"/><RequestState loading={isLoading} error={error}/>{!isLoading&&!error&&<p className="empty">数据库中尚无MRV运行。</p>}</>;
  return <><Header eyebrow="SCREENING MRV" title="筛选级碳核算" sub={run.functional_unit}/><div className="status"><Badge tone={run.conclusion_status==='indeterminate'?'warn':'ok'}>{run.conclusion_status.toUpperCase()}</Badge><h2>{run.conclusion_status==='indeterminate'?'当前不能确认减排结论':'筛选结果已生成'}</h2><p>单位：{run.unit_intensity}</p></div><section className="metrics three"><article><small>基准</small><b>{run.baseline_emissions}</b></article><article><small>项目</small><b>{run.project_emissions}</b></article><article><small>差值</small><b>{run.difference}</b></article></section><div className="panel"><h2>缺失与门控</h2>{run.missing_items.length?<ul>{run.missing_items.map(item=><li key={item}>{item}</li>)}</ul>:<p>无关键缺失项</p>}</div><div className="sensitivity">{Object.entries(run.sensitivity).map(([name,value])=><span key={name}>{name}: 基准 {value.baseline} / 项目 {value.project} / 差值 {value.difference}</span>)}</div></>;
}

export function Evidence(){
  const {data,error,isLoading}=useSWR<EvidenceRecord[]>('/api/v1/evidence',fetcher);
  return <><Header eyebrow="EVIDENCE REGISTER" title="证据台账" sub="数据来自EvidenceArtifact表。"/><RequestState loading={isLoading} error={error}/>{data?.map(record=><article className="evidence" key={record.id}><Badge>背景证据</Badge><div><h2>{record.name}</h2><b>{record.file_reference??record.status}</b><p>{record.limitations}</p></div></article>)}</>;
}

export function Claims(){
  const [text,setText]=useState('世界首创的零碳系统'); const [result,setResult]=useState<any>(null); const [error,setError]=useState('');
  async function submit(event:FormEvent){event.preventDefault();setResult(null);setError('');try{setResult(await api('/api/v1/claims/check',{method:'POST',body:JSON.stringify({text})}))}catch(err){setError(err instanceof Error?err.message:'主张检查服务不可用')}}
  return <><Header eyebrow="CLAIM GATE" title="主张边界检查" sub="规则化检查由后端执行。"/><form className="claim-form" onSubmit={submit}><textarea aria-label="宣传表述" value={text} onChange={e=>setText(e.target.value)}/><button className="button">检查表述</button></form>{error&&<p role="alert" className="error">无法检查：{error}</p>}{result&&<div className={`claim-result ${result.result}`}><Badge tone={result.result==='block'?'danger':'ok'}>{result.result.toUpperCase()}</Badge><h2>{result.result==='block'?'该表述已拦截':'该表述通过'}</h2>{result.hits?.map((hit:any,index:number)=><article key={index}><b>命中：{hit.matched_terms.join('、')}</b><p>{hit.reason}</p><p>规则改写：{hit.suggested_rewrite}</p></article>)}<p><strong>组合改写：</strong>{result.suggested_rewrite}</p></div>}</>;
}

export function Verify(){
  const {certificateId}=useParams(); const navigate=useNavigate(); const location=useLocation();
  const initialManifest=(location.state as {manifest?:Record<string,unknown>}|null)?.manifest??null;
  const [manifest,setManifest]=useState<Record<string,unknown>|null>(initialManifest); const [state,setState]=useState<'idle'|'valid'|'invalid'|'needs_payload'|'unavailable'>('idle'); const [error,setError]=useState('');
  async function submitVerification(kind:'normal'|'input'|'result'='normal'){
    setState('idle');setError('');
    try{const payload:Record<string,unknown>={};if(manifest)payload.manifest=manifest;if(kind==='input')payload.input_snapshot={tampered:true};if(kind==='result')payload.result_snapshot={tampered:true};const response:any=await api(`/api/v1/certificates/${certificateId}/verify`,{method:'POST',body:JSON.stringify(payload)});if(response.status==='needs_payload')setState('needs_payload');else setState(response.valid?'valid':'invalid')}
    catch(err){setState('unavailable');setError(err instanceof Error?err.message:'证书服务不可用')}
  }
  async function create(){
    setState('idle');setError('');
    try{const batches=await api<Batch[]>('/api/v1/batches');if(!batches.length)throw new Error('数据库中没有可签发批次');const batch=await api<Batch>(`/api/v1/batches/${batches[0].id}`);const response:any=await api('/api/v1/certificates',{method:'POST',body:JSON.stringify({input_snapshot:batch,result_snapshot:batch.calculations??{}})});setManifest(response.manifest);navigate(`/verify/${response.certificate_id}`,{state:{manifest:response.manifest}})}
    catch(err){setState('unavailable');setError(err instanceof Error?err.message:'证书服务不可用')}
  }
  async function upload(file:File|undefined){setError('');if(!file)return;if(file.size>2*1024*1024){setError('manifest超过2 MiB限制');return}try{setManifest(JSON.parse(await file.text()));setState('idle')}catch{setManifest(null);setError('manifest不是有效JSON')}}
  return <><Header eyebrow="PUBLIC VERIFICATION" title={certificateId?`证书 ${certificateId}`:'证书验证'} sub="调用者必须提交manifest或完整输入结果；空请求绝不判定有效。"/>{certificateId==='new'?<button className="button" onClick={create}>从数据库批次生成证书</button>:<div className="toolbar"><a className="button" href={`/api/v1/certificates/${certificateId}/manifest`} download="certificate-manifest.json">下载manifest</a><label className="upload">上传manifest<input aria-label="上传manifest" type="file" accept="application/json,.json" onChange={e=>upload(e.target.files?.[0])}/></label><button className="button" onClick={()=>submitVerification()}>验证完整性</button></div>}{manifest&&<p role="status">已加载manifest：{String(manifest.certificate_id??'未知证书')}</p>}{certificateId!=='new'&&manifest&&<div className="toolbar"><button onClick={()=>submitVerification('input')}>模拟修改输入</button><button onClick={()=>submitVerification('result')}>模拟修改结果</button></div>}{state==='needs_payload'&&<p role="alert" className="error">需要上传manifest或提交完整输入与结果。</p>}{state==='unavailable'&&<p role="alert" className="error">无法验证：{error}</p>}{error&&state!=='unavailable'&&<p role="alert" className="error">{error}</p>}{(state==='valid'||state==='invalid')&&<div className={`verify ${state}`}><Badge tone={state==='valid'?'ok':'danger'}>{state==='valid'?'验证成功':'验证失败'}</Badge><h2>{state==='valid'?'输入与结果哈希匹配':'证书绑定已被修改'}</h2></div>}<article className="boundary"><h2>证书边界</h2><p>证明计算来源和文件完整性。不证明采样真实性，不证明算法科学结论正确，不等于第三方核证或碳信用。</p></article></>;
}

export function About(){return <><Header eyebrow="ABOUT S-PROOF" title="运行与证据系统，不是碳交易平台。" sub="比赛版本聚焦可追溯、可复算和边界诚实。"/><div className="panel"><h2>当前边界</h2><p>不替代SCADA，不自动控制装置，不提供碳信用，不宣称已核证LCA。</p><Link className="button" to="/verify/new">生成数据库证书</Link></div></>}
