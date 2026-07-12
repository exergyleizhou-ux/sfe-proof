import React from 'react';
export function Badge({tone='neutral',children}:{tone?:'neutral'|'warn'|'danger'|'ok',children:React.ReactNode}){return <span className={`badge ${tone}`}>{children}</span>}
export function ProvenanceWarning(){return <Badge tone="warn">第三方实验室送样检测，不等于第三方现场采样</Badge>}
