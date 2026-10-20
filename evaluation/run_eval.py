#!/usr/bin/env python3
"""Run a small repeatable Ollama coding evaluation and save raw evidence."""
from __future__ import annotations
import argparse, json, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', default='photon1', help='Exact local Ollama model name')
    ap.add_argument('--host', default='http://127.0.0.1:11434')
    ap.add_argument('--cases', type=Path, default=Path(__file__).with_name('cases.json'))
    ap.add_argument('--output', type=Path, default=None)
    ap.add_argument('--limit', type=int, default=0, help='Run first N cases only')
    ap.add_argument('--timeout', type=int, default=240)
    args = ap.parse_args()
    cases = json.loads(args.cases.read_text(encoding='utf-8'))
    if args.limit: cases = cases[:max(1,args.limit)]
    results=[]
    for case in cases:
        prompt = ('You are Photon 1 inside Incandescent. Sound natural and direct, follow constraints exactly, and do not claim to execute code.\n\n' + case['prompt'])
        body = json.dumps({'model':args.model,'stream':True,'messages':[{'role':'user','content':prompt}], 'options':{'temperature':0.0,'num_ctx':4096,'num_predict':int(case.get('max_tokens',256)),'repeat_penalty':1.05}, 'keep_alive':'5m'}).encode()
        req=urllib.request.Request(args.host.rstrip('/')+'/api/chat',data=body,headers={'Content-Type':'application/json','Accept':'application/x-ndjson'},method='POST')
        started=time.perf_counter(); first_token=None; pieces=[]; error=None
        try:
            with urllib.request.urlopen(req,timeout=args.timeout) as response:
                for raw in response:
                    if not raw.strip(): continue
                    item=json.loads(raw.decode('utf-8'))
                    if item.get('error'): raise RuntimeError(item['error'])
                    content=item.get('message',{}).get('content','')
                    if content:
                        if first_token is None: first_token=time.perf_counter()-started
                        pieces.append(content)
                    if item.get('done'): break
        except Exception as exc: error=f'{type(exc).__name__}: {exc}'
        elapsed=time.perf_counter()-started; answer=''.join(pieces)
        low=answer.casefold()
        phrase_checks={phrase:phrase.casefold() in low for phrase in case.get('required_phrases',[])}
        any_checks={phrase:phrase.casefold() in low for phrase in case.get('required_any',[])}
        heuristic_pass=bool(answer) and error is None and all(phrase_checks.values()) and (not any_checks or any(any_checks.values()))
        result={'id':case['id'],'category':case['category'],'prompt':case['prompt'],'response':answer,'error':error,'elapsed_seconds':round(elapsed,3),'time_to_first_token_seconds':round(first_token,3) if first_token is not None else None,'response_chars':len(answer),'phrase_checks':phrase_checks,'required_any_checks':any_checks,'heuristic_pass':heuristic_pass}
        results.append(result)
        status='ERROR' if error else ('PASS' if result['heuristic_pass'] else 'REVIEW')
        print(f"[{status}] {case['id']}: {result['elapsed_seconds']}s, TTFT={result['time_to_first_token_seconds']}, chars={len(answer)}")
        if error: print('  '+error)
    summary={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'model':args.model,'host':args.host,'case_count':len(results),'heuristic_pass_count':sum(1 for r in results if r['heuristic_pass']),'error_count':sum(1 for r in results if r['error']),'mean_latency_seconds':round(sum(r['elapsed_seconds'] for r in results)/len(results),3) if results else None,'mean_ttft_seconds':round(sum(r['time_to_first_token_seconds'] for r in results if r['time_to_first_token_seconds'] is not None)/max(1,sum(1 for r in results if r['time_to_first_token_seconds'] is not None)),3) if any(r['time_to_first_token_seconds'] is not None for r in results) else None,'warning':'Phrase checks are smoke-test heuristics, not a correctness or Claude-comparability score. Human review and actual code tests are still required.','results':results}
    output=args.output or Path(__file__).with_name('results')/('eval-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f"Saved full outputs to {output}")
    return 1 if summary['error_count'] else 0
if __name__=='__main__': raise SystemExit(main())
