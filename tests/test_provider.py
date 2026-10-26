"""No network calls: validate the hosted boundary and secret handling."""
import json
import os
import unittest
from unittest.mock import patch
from src.provider import Client,ProviderError

class FakeResponse:
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self):
        return json.dumps({'candidates':[{'content':{'parts':[{'text':'test response'}]},'finishReason':'STOP'}],
                           'modelVersion':'gemini-test-001','usageMetadata':{'promptTokenCount':20}}).encode()

class ProviderTests(unittest.TestCase):
    def test_hosted_request_and_metadata(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':'unit-test-key-value','GEMINI_MIN_INTERVAL':'0'}):
            with patch('src.provider.urlopen',return_value=FakeResponse()) as send:
                client=Client(); text,seconds=client.complete('trusted system','text report',13)
                request=send.call_args.args[0]
                self.assertTrue(request.full_url.startswith('https://generativelanguage.googleapis.com/'))
                self.assertNotIn('unit-test-key-value',request.data.decode())
                payload=json.loads(request.data)
                self.assertEqual(payload['contents'][0]['parts'][0]['text'],'text report')
                config=payload['generationConfig']
                self.assertNotIn('seed',config)
                self.assertEqual(config['temperature'],0.2)
                self.assertEqual(config['maxOutputTokens'],512)
                self.assertEqual(config['responseMimeType'],'application/json')
                schema=config['responseSchema']
                self.assertEqual(schema['propertyOrdering'],['Thought','Action','Final Report'])
                self.assertEqual(set(schema['required']),{'Thought','Action','Final Report'})
                self.assertTrue(all(v['type']=='STRING' for v in schema['properties'].values()))
                self.assertEqual(client.metadata['revision'],'gemini-test-001')
                self.assertIsNone(client.metadata['decoding_seed'])
                self.assertEqual(text,'test response')

    def test_missing_key_has_no_network_or_local_fallback(self):
        with patch.dict(os.environ,{},clear=True),patch('src.provider.urlopen') as send:
            with self.assertRaises(ProviderError): Client().complete('system','report')
            send.assert_not_called()

if __name__=='__main__': unittest.main()
