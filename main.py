import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import sys
import json
import requests
import uuid
import os

# LINE Bot APIの設定
LINE_BOT_API_URL = 'https://api.line.me/v2/bot/message/broadcast'
LINE_BOT_API_TOKEN = os.environ['API_KEY']

print("input/output デバイス一覧")
print(sd.query_devices())

# サンプリング周波数を取得
device_info = sd.query_devices(sd.default.device[0], 'input')
samplerate = int(device_info['default_samplerate'])

# 入力デバイスを表示
print("===> 入力デバイス識別子:{} 詳細: {}".format(sd.default.device[0], device_info))

q = queue.Queue()

def recordCallback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

# 言語モデルと音声識別機能を構築
print("===> 言語モデルと音声識別機能を構築しています。 この処理には時間が掛かる時があります。")
model = Model("../LoRaInteractionTest_RM-92C/model")  # モデルのパスを選択
recognizer = KaldiRecognizer(model, samplerate) # モデルを使用して、音声をテキストに変換
recognizer.SetWords(False)  # 「False」を選択することで、出力が各単語ではなく文章形式のみに制限される

print("===> マイクから音声を取得しています。 取得を止める際には、「ctrl + c」を押してください。")
# 音声データをキャプチャしてテキストに書き起こす
try:
    with sd.RawInputStream(dtype='int16',
                           channels=1,
                           callback=recordCallback):
        while True:
            # キューにあるデータを取得
            data = q.get()
            if recognizer.AcceptWaveform(data):
                recognizerResult = recognizer.Result()
                # recognizerResultの文字列を辞書型に変換
                resultDict = json.loads(recognizerResult)
                # "text"にデータが入っているか
                if not resultDict.get("text", "") == "":
                    # データを出力
                    print(resultDict["text"])

                    # LINEに送信
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + LINE_BOT_API_TOKEN,
                        'X-Line-Retry-Key': str(uuid.uuid4())
                    }

                    data = {
                        "messages": [
                            {
                                "type": "text",
                                "text": resultDict["text"]
                            }
                        ]
                    }

                    response = requests.post(LINE_BOT_API_URL, headers=headers, json=data)

                    if response.status_code != 200:
                        print("Failed to send message.")
                    else:
                        print("Message sent successfully!")
                    break

                else:
                    print("入力された音声がありません")

except KeyboardInterrupt:
    print('===> 音声の取得を停止')
except Exception as e:
    print(str(e))
