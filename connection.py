import requests, json
import io, time

from typing import Optional, Dict

class VoiceVox():
    def __init__(self, host:str='127.0.0.1', port:int=50021) -> bool:
        self.url = f'http://{host}:{port}/'

    def ready(self, speaker_id: int) -> None:
        try:
            headers = {'accept': '*/*'}
            params = (
                ('speaker', speaker_id),
                ('skip_reinit', True)
            )
            responce = requests.get(
                self.url + 'initialize_speaker',
                params=params,
                headers=headers
            )
        except requests.exceptions.ConnectionError:
            raise ConnectionError('VoiceVoxとの接続に失敗しました。VoiceVoxを起動していない場合は立ち上げた状態で実行してください。')
        return responce.status_code == requests.status_codes.codes.no_content
    
    def synth(self, text: str, speaker_id: int, extra: Dict = {}, debug: bool=False) -> Optional[io.BytesIO]:
        start = time.time()
        debug = not debug
        try:
            params1 = (
                ('text', text),
                ('speaker', speaker_id),
            )
            response1 = requests.post(
                self.url + 'audio_query',
		        params=params1,
	        )
            headers = {'Content-Type': 'application/json',}
            data = response1.json()
            data.update(extra)
            data['outputSamplingRate'] = 48000 * 2
            data['kana'] = 'string'
            response2 = requests.post(
                self.url + 'synthesis',
		        headers=headers,
		        params=params1,
		        data=json.dumps(data)
	        )
            assert debug, '生成時間： ' + str(time.time()-start)
            return io.BytesIO(response2.content)
        except requests.exceptions.ConnectionError:
            raise ConnectionError('VoiceVoxとの接続に失敗しました。VoiceVoxを起動していない場合は立ち上げた状態で実行してください。')
    
    @property
    def speakers(self) -> Dict:
        speakers : Dict[str, Dict[str,int]] = {}
        try:
            responce = requests.get(
                self.url + 'speakers',
            )
        except requests.exceptions.ConnectionError:
            raise ConnectionError('VoiceVoxとの接続に失敗しました。VoiceVoxを起動していない場合は立ち上げた状態で実行してください。')
        for speaker in responce.json():
            style_id = {}
            for style in speaker['styles']:
                style_id[style['name']] = int(style['id'])
            speakers[speaker['name']] = style_id
        return speakers