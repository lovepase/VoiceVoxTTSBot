from discord.ext import commands
from discord import Colour, Embed, Intents, Game, Status, TextChannel, User

import os, time, socket, asyncio
import configparser

from logger import Logger
from typing import Union
from pathlib import Path

from utils import Utils

exts = ['ttscog']
environment = 'DEVELOPMENT'

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

class MyHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping) -> None:
        prefix = bot.command_prefix
        embed = Embed(
            title="TTSBot Help",
            color=Colour.gold(),
            description=f'スラッシュコマンド（推奨）か{prefix}を先頭につけたコマンドのどちらかで実行できます。'
        )
        embed.add_field(name=f'/vc join または {prefix}vc join',value='ボイスチャンネルに参加します。',inline=False)
        embed.add_field(name=f'/vc leave または {prefix}vc leave', value='ボイスチャンネルから退出します。',inline=False)
        embed.add_field(name=f'/voice または {prefix}voice', value=f'現在のユーザーに割り当てられた話者を表示します。無い場合は新たに割り振ります。',inline=False)
        embed.add_field(name=f'/set_voice <speaker_id> (style_id 任意) (pitch 任意) (speed 任意) (volume 任意)', value=f'speaker_idの項目にカーソルを合わせると話者の候補が表示されます。style_id以降の入力は任意です。',inline=False)
        embed.add_field(name=f'> style_id', value=f'speaker_idを候補から選択すると、それに対応する話者のスタイル（感情など）をstyle_idから選択することが出来ます。（入力しなかった場合はノーマルになります）',inline=False)
        embed.add_field(name=f'> pitch speed volume', value=f'ユーザーの音声を入力したピッチ、スピード、ボリュームにセットします。上限と下限は以下の通りです。\n-1.0<pitch(デフォルトは0)<1.0\n0.5<speed(デフォルトは1)<2.0\n0.5<volume(デフォルトは1)<2.0\nこの値は話者の変更やBotの再起動でリセットされます。',inline=False)
        channel = self.get_destination()
        return await channel.send(embed=embed)

class TTSBot(commands.Bot):
    def __init__(self, config):
        self.config = config
        self.prefix = config.get('PREFIX', '!')
        self.utils = Utils()
        super().__init__(command_prefix=self.prefix, intents=Intents.all(), help_command=MyHelpCommand())

    async def addReaction(self, ctx, reaction: str, message: str = None):
        if ctx.interaction == None:
            return await ctx.message.add_reaction(reaction)
        return await ctx.send(message, silent=True)
    
    async def sendMessage(self, ctx, message: str):
        if ctx.interaction == None:
            return await ctx.channel.send(message, silent=True)
        return await ctx.send(message, silent=True)
    
    async def sendEmbed(self, ctx: Union[commands.Context, TextChannel], title: str, user: User = None):
        embed = Embed(title=title,color=Colour.dark_gold())
        if user is not None:
            if type(ctx) == commands.Context and ctx.interaction is not None:
                return await ctx.send(embed=embed, silent=True, ephemeral=True)
        return await ctx.send(embed=embed, silent=True)

bot = TTSBot(config=config[environment])
bot.logger = Logger.logger("TTSBot")

@bot.event
async def on_ready():
    bot.logger.info('起動しました')
    bot.logger.info('現在のユーザー名： ' + bot.user.name)
    bot.logger.info('現在のユーザーID： ' + str(bot.user.id))
    bot.logger.info('現在のコマンドプリフィックス： ' + bot.command_prefix)
    await change_status()
    if config[environment].getboolean('SYNC',False):
        await bot.tree.sync()

async def change_status() -> None:
    await bot.change_presence(activity=Game(f"{bot.command_prefix}helpでコマンドヘルプを表示します"), status=Status.online)

async def load_cogs() -> None:
    for ext in exts:
        await bot.load_extension(ext)

hostok = ['localhost', '127.0.0.1', 'app://']
def isConnectable(host, port) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
            c.connect((host,port))
    except socket.error:
        return False
    return True

def app_execute(host, port, interval=1.,retries=5):
    voicevox_dir = config[environment].get('VOICEVOX_DIR')
    if voicevox_dir is None:
        bot.logger.error('VOICEVOXのパスが設定されていません（VOICEVOXを起動した状態で実行するかconfig.ini に VOICEVOX_DIR = <VOICEVOX.exeがあるディレクトリ> を設定してください）')
        raise FileNotFoundError()
    path = Path(voicevox_dir) / "VOICEVOX.exe"
    if path.exists():
        os.system(f'powershell -Command "{path.absolute()}"')
    else:
        bot.logger.error('パスが見つかりませんでした')
        raise FileNotFoundError()
    
    for _ in range(retries):
        time.sleep(interval)
        if isConnectable(host, port):
            bot.logger.info('起動しました')
            break
    else:
        bot.logger.error('VoiceVoxを起動出来ませんでした')
        raise RuntimeError()

TOKEN = config[environment].get('TOKEN')
host = config[environment].get('HOST', '127.0.0.1')
port = config[environment].getint('PORT', 50021)
debug = config[environment].getboolean('DEBUG', False)

if __name__ == '__main__':
    if host not in hostok:
        bot.logger.warning(f"ホストは{','.join(hostok)}のどれかに設定してください")
    if not isConnectable(host, port):
        bot.logger.info('config.iniのパスをもとにVOICEVOXを起動します')
        app_execute(host, port)
    if TOKEN is None or 'TOKEN' in TOKEN:
        TOKEN = input('Botのトークンを入力してください。(config.iniに TOKEN = <Discord TOKEN> を設定することで次回からの入力をスキップ出来ます。)')
    asyncio.run(load_cogs())
    bot.run(TOKEN)