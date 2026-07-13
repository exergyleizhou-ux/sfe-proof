export async function api<T>(path:string, init?:RequestInit):Promise<T>{
  const headers:Record<string,string>={...(init?.headers as Record<string,string>||{})};
  if(init?.body && !(init.body instanceof FormData)) headers['Content-Type']='application/json';
  let response:Response;
  try{response=await fetch(path,{...init,headers})}catch{throw new Error('后端服务不可用')}
  if(!response.ok){const body=await response.json().catch(()=>({detail:'请求失败'}));throw new Error(typeof body.detail==='string'?body.detail:'请求失败')}
  return response.json()
}
