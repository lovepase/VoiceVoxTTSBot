# Voicevox TTSBot

VoiceVoxを使用したDiscord Bot

# Features

VoiceVoxを利用する読み上げBotです。

VoiceVoxは別途立ち上げるか、exeがあるディレクトリを設定する必要があります。

# Usage

必要なパッケージやVoiceVoxをインストールしたら、config.iniの必要な項目を入力してbot.pyを実行してください。


## 初めて実行する場合

初めて実行するときはconfig.iniのSYNCをTrueにして実行してください。

その際にスラッシュコマンドが登録されますが、登録には時間がかかる場合があります。

それ以降はSYNCをFalseにして実行してください。

## コマンド一覧
Botのステータスに記載しているhelpからコマンドの一覧を見れます

- vc join / vc leave　:　ユーザーのいるボイスチャンネルに参加/退出します
- set <speaker_id> / set_voice <speaker_id> <style_id>　：　指定したIDの音声をユーザーに適用します。スラッシュコマンドの場合はspeaker_idの候補が表示され、選択するとその音声に選択可能なstyle_id（感情など）を候補から選べるようになります。また同時に音声のピッチ、スピード、ボリュームを入力することが出来ます。
- voice　：　現在ユーザーに割り当てられている音声を表示します。

## config.iniの設定
クオーテーションをつけずに入力してください

- TOKEN = <Botのトークン>
- PREFIX = <コマンドの先頭につける文字>　（項目が無い場合はデフォルト値の「!」が使用されます）
- VOICEVOX_DIR = <VOICEVOX.exeがあるディレクトリ> （VoiceVoxが立ち上がっていない場合はここから.exeを実行します）
- SYNC = True / False　（Trueの場合Botのスラッシュコマンドを同期します。初回のみTrueにして実行してください）

# Details

VoiceVoxを立ち上げたときに立つ、localhost（あるいは127.0.0.1など）のHTTPサーバと通信することで音声を合成します。

合成した音声はffmpegを使用せずに生の音声データで渡されるためffmpegは不要です。（ffmpegを使用したほうがどのくらい早いかは未検証）

HTTPサーバが立っていればGUIは不要です。

ユーザーと話者のUUIDはサーバーごとにjsonで保存されます。
data/<guild_id>.json

ファイルが無い場合は新しく生成されます。

ピッチ、スピード、ボリュームは保存されません。

# Requirement

* Python 3
* VoiceVox (GUI版)
* 使用パッケージはrequirements.txtに記載

# Note

## 実装出来たら良いなと思うもの

GUI版 => Dockerイメージを使用

辞書機能や禁止ワードの設定など

speaker_idの候補表示が最大で25なのでさらに多くの候補を選択可能にする

YouTubeやニコニコ動画を再生できるCogを追加する

# Credits

VoiceVoxを利用させていただきました
