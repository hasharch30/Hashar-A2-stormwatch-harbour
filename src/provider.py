"""Hosted Gemini REST client; credentials come only from the process environment."""
import json
import os
import time
import re
import threading
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

MODEL=os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite')
TEMPERATURE=0.2
LOG_LOCK=threading.Lock()
RESPONSE_SCHEMA={'type':'OBJECT','properties':{key:{'type':'STRING'} for key in ['Thought','Action','Final Report']},
                 'required':['Thought','Action','Final Report'],'propertyOrdering':['Thought','Action','Final Report']}

class ProviderError(RuntimeError):
    pass

class Client:
    _last_started=0.0
    _rate_lock=threading.Lock()

    @classmethod
    def pace(cls):
        with cls._rate_lock:
            interval=float(os.getenv('GEMINI_MIN_INTERVAL','6.2'))
            delay=interval-(time.monotonic()-cls._last_started)
            if delay>0:
                time.sleep(delay)
            cls._last_started=time.monotonic()

    def __init__(self):
        self.model=MODEL
        self.metadata={'provider':'Google Gemini API','model':self.model,
                       'temperature':TEMPERATURE,'revision':'not yet returned by API'}

    def complete(self,system,user,seed=1):
        key=os.getenv('GEMINI_API_KEY')
        if not key:
            raise ProviderError('Set GEMINI_API_KEY for hosted calls, or use --replay with saved logs.')
        body={'systemInstruction':{'parts':[{'text':system}]},
              'contents':[{'role':'user','parts':[{'text':user}]}],
              'generationConfig':{'temperature':TEMPERATURE,'maxOutputTokens':512,
                                  'responseMimeType':'application/json','responseSchema':RESPONSE_SCHEMA}}
        url=f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent'
        request=Request(url,json.dumps(body).encode(),{'Content-Type':'application/json','x-goog-api-key':key})
        started=None
        failures=0
        for transport_attempt in range(3):
            self.pace()
            if started is None:
                started=time.perf_counter()
            try:
                with urlopen(request,timeout=45) as response:
                    data=json.load(response)
                break
            except HTTPError as exc:
                # Never include the request headers or key in errors/logs.
                try:
                    message=json.loads(exc.read()).get('error',{}).get('message','HTTP failure')
                except Exception:
                    message='HTTP failure'
                message=message.replace(key,'[redacted]')
                failures+=1
                tick=re.search(r'^tick=(\d+)$',user,re.M)
                error_record={'provider':'Google Gemini API','model':self.model,
                              'tick':int(tick[1]) if tick else None,'request_tag':seed,'decoding_seed':None,
                              'system':system,'prompt':user,'http_status':exc.code,'response':message,
                              'date':datetime.now(timezone.utc).isoformat()}
                Path('logs').mkdir(exist_ok=True)
                with LOG_LOCK:
                    with Path('logs/provider_errors.jsonl').open('a',encoding='utf-8') as f:
                        f.write(json.dumps(error_record)+'\n')
                transient=exc.code in (500,502,503,504)
                if transient and transport_attempt<2:
                    time.sleep(10*(transport_attempt+1))
                    continue
                raise ProviderError(f'Gemini HTTP {exc.code}: {message}. No local model was called.') from None
            except (TimeoutError,URLError) as exc:
                failures+=1
                tick=re.search(r'^tick=(\d+)$',user,re.M)
                error_record={'provider':'Google Gemini API','model':self.model,
                              'tick':int(tick[1]) if tick else None,'request_tag':seed,'decoding_seed':None,
                              'system':system,'prompt':user,'http_status':'transport_error',
                              'response':str(exc).replace(key,'[redacted]'),
                              'date':datetime.now(timezone.utc).isoformat()}
                Path('logs').mkdir(exist_ok=True)
                with LOG_LOCK:
                    with Path('logs/provider_errors.jsonl').open('a',encoding='utf-8') as f:
                        f.write(json.dumps(error_record)+'\n')
                if transport_attempt<2:
                    time.sleep(10*(transport_attempt+1))
                    continue
                raise ProviderError('Gemini connection failed after three attempts. Saved outputs can be resumed.') from None
        elapsed=time.perf_counter()-started
        candidates=data.get('candidates',[])
        text=''.join(p.get('text','') for p in (candidates[0].get('content',{}).get('parts',[]) if candidates else [])
                     if not p.get('thought',False))
        self.metadata={'provider':'Google Gemini API','model':self.model,
                       'revision':data.get('modelVersion',self.model),
                       'temperature':TEMPERATURE,'usage':data.get('usageMetadata',{}),
                       'response_id':data.get('responseId'),
                       'finish_reason':candidates[0].get('finishReason') if candidates else 'BLOCKED',
                       'max_output_tokens':512,'decoding_seed':None,'request_tag':seed,
                       'response_format':'ordered ReAct JSON','http_failures_before_response':failures}
        return text,elapsed
