from ctypes import util
import io, re

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from discord import Interaction, VoiceClient
from discord import PCMAudio

from typing import List, Dict, Optional, Union
from pathlib import Path
import random, math, asyncio
import alkana

from utils import Utils
from connection import VoiceVox

utils = Utils()

class AudioQueue(asyncio.Queue):
    def __init__(self, tts, voice_client) -> None:
        self.tts : TTSCog = tts
        self.voice_client : VoiceClient = voice_client
        self.task : asyncio.Task = None
        super().__init__(10)
        
    async def play_queue(self) -> None:
        if self.task is None or self.task.done:
            self.task = asyncio.get_running_loop().create_task(self._exc_queue())
            await self.task

    def _exc_queue(self) -> None:
        while not self.empty():
            if self.voice_client.is_playing():
                yield
                continue
            text, speaker_id, extra = self.get_nowait()
            audio = PCMAudio(io.BufferedReader(self.tts.voicevox.synth(text, speaker_id, extra)))
            audio.read() # 一度readして先頭のノイズをスキップ
            self.voice_client.play(audio)
            self.task_done()
            yield

class ExtraData():
    default = {'pitchScale':0.0,'speedScale':1.0,'volumeScale':1.0}
    def __init__(self, input_data: Optional[Dict]) -> None:
        self.data = {}
        data = input_data if input_data else {}
        for key in self.default.keys():
            self.data[key] = data.pop(key,self.default[key])
    
    @staticmethod
    def get_by_psv(pitch, speed, volume):
        return ExtraData({'pitchScale':pitch,'speedScale':speed,'volumeScale':volume})

    def extractText(self, join_text: str = ' ') -> str:
        opts = []
        for key in self.default.keys():
            val0 = self.default[key]
            val1 = self.data[key]
            if type(val0) == type(val1) == float:
                opts.append(f'{key}:{self.data[key]}' if not math.isclose(val0, val1, abs_tol=1e-5) else '')
            else:
                opts.append(f'{key}:{str(self.data[key])}')
        return join_text.join(opts)

    def extract(self) -> Dict:
        out = self.data.copy()
        out["pitchScale"] = max(-1.,min(1.,self.data["pitchScale"]))
        out["speedScale"] = max(0.5,min(2.,self.data["speedScale"]))
        out["volumeScale"]= max(0.5,min(2.,self.data["volumeScale"]))
        out['pitchScale'] /= 10.0
        return out

class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue: Dict[AudioQueue] = {}
        self._channelIDs: List[int] = []
        self.voicevox = VoiceVox()
        self.speakers = self.voicevox.speakers
        self.speakerIDs = {id:name + ' ' + style for name, styles in self.speakers.items() for style, id in styles.items()}
        self._user_voice_dic : Dict[int, Dict] = {}
        self._user_extra_dic = {}
        self._commandNames: List[str] = [c.name for c in self.get_commands()]
        super().__init__()

    async def speaker_autocomplete(self, interaction: Interaction, cor: str) -> List[app_commands.Choice[int]]:
        max_choice = 25
        completes : List[app_commands.Choice[int]] = []
        for name, styles in self.speakers.items():
            if max_choice <= len(completes):
                break
            id = int(list(styles.values())[0])
            completes.append(app_commands.Choice(name=name, value=id))
        return completes

    async def speaker_style_autocomplete(self, interaction: Interaction, cor: str) -> List[app_commands.Choice[int]]:
        max_choice = 25
        speaker_id = interaction.data['options'][0]['value']
        speaker_name = self.speakerIDs[speaker_id].split(' ')[0]
        if speaker_name not in self.speakers.keys():
            return []
        completes : List[app_commands.Choice[int]] = []
        for style, id in self.speakers[speaker_name].items():
            if max_choice <= len(completes):
                break
            completes.append(app_commands.Choice(name=style, value=id))
        return completes

    @commands.hybrid_command(
        name='set_voice',
        description='Assign a speaker to the user',
        aliases=['set'],
        option=[
            {
                "name": "speaker",
                "description": "speaker_id",
                "type": 4,
                "required": True,
                "autocomplete": True
            },
            {
                "name": "style",
                "description": "speaker's style",
                "type": 4,
                "required": False,
                "autocomplete": True
            },
            {
                "name": "pitch",
                "description": "default value = 0.0",
                "type": 10,
                "required": False,
                "min_value": -1.0,
                "max_value": 1.0,
            },
            {
                "name": "speed",
                "description": "default value = 1.0",
                "type": 10,
                "required": False,
                "min_value": 0.5,
                "max_value": 2.0,
            },
            {
                "name": "volume",
                "description": "default value = 1.0",
                "type": 10,
                "required": False,
                "min_value": 0.5,
                "max_value": 2.0,
            }
        ]
    )
    @app_commands.autocomplete(speaker_id=speaker_autocomplete, style_id=speaker_style_autocomplete)
    async def set_voice(self, ctx: Context, speaker_id: int, style_id: int = -1, pitch:float = 0.0, speed:float = 1., volume:float = 1.):
        if speaker_id not in self.speakerIDs:
            return await self.bot.sendEmbed(ctx, f"id={speaker_id}が見つかりませんでした")
        if style_id < 0:
            style_id = speaker_id
        self.voicevox.ready(style_id)
        self.set_user_voice(ctx.author.id, ctx.guild.id, style_id)
        speaker_name = self.speakerIDs[style_id]
        data = ExtraData.get_by_psv(pitch=pitch, speed=speed, volume=volume)
        extra_text = data.extractText()
        self._user_extra_dic[ctx.author.id] = data.extract()
        return await self.bot.sendEmbed(ctx, f"{speaker_name} {extra_text} に設定しました")


    @commands.hybrid_command(
        name='voice',
        description='display your voice',
    )
    async def voice(self, ctx: Context):
        await self.voiceInfo(ctx)

    async def voiceInfo(self, ctx:Context, *, sendTo: Union[discord.TextChannel, Context] = None, prefix = '', suffix = ''):
        speaker_id = self.user_voice(ctx.author.id, ctx.guild.id)
        speaker_name = self.speakerIDs[speaker_id]
        extra_text = ExtraData(self._user_extra_dic.get(ctx.author.id)).extractText()
        return await self.bot.sendEmbed(ctx, prefix + f"{speaker_name} {extra_text}" + suffix, sendTo=sendTo)

    @commands.hybrid_group(
        name='vc',
        description='vc commands'
    )
    async def vc(self, ctx: Context):
        return

    @vc.command(
        name='join',
        description='connect to the channel',
    )
    async def join(self, ctx: Context):
        if ctx.author.voice is None:
            return await self.bot.sendEmbed(ctx, "あなたはボイスチャンネルに参加していません")
        channel = ctx.author.voice.channel
        connecting_channelIDs = [voice_client.channel.id for voice_client in self.bot.voice_clients]
        if channel in connecting_channelIDs:
            return await self.bot.sendEmbed(ctx, "既にボイスチャンネルに参加しています")
        for member in channel.members:
            if member.bot:
                continue
            self.voicevox.ready(self.user_voice(member.id, member.guild.id)) # vcに入った時点で既にいたユーザーに割り振り
        self._channelIDs.append(ctx.channel.id)
        self._user_voice_dic[ctx.guild.id] = utils.FileUtil.read_by_guild(ctx.guild.id)
        return await channel.connect(), await self.bot.sendEmbed(ctx, "ボイスチャンネルに接続しました")
    
    @vc.command(
        name='leave',
        description='disconnect from the channel',
    )
    async def leave(self, ctx: Context):
        channel = ctx.author.voice.channel
        connecting_channelIDs = [voice_client.channel.id for voice_client in self.bot.voice_clients]
        if channel.id not in connecting_channelIDs:
            return await self.bot.sendEmbed(ctx, "あなたのいるボイスチャンネルに参加していません")
        if ctx.channel.id in self._channelIDs:
            self._channelIDs.remove(ctx.channel.id)
        await self.bot.addReaction(ctx, '✅', "ボイスチャンネルから退出します")
        return await ctx.guild.voice_client.disconnect(), await self.bot.sendEmbed(ctx, "切断しました")

    @commands.Cog.listener(name='on_message')
    async def on_message(self, message) -> None:
        if message.content.startswith(self.bot.command_prefix):
            return
        if message.author.bot:
            return
        if message.channel.id not in self._channelIDs:
            return
        speaker_id = self.user_voice(message.author.id, message.guild.id)
        text = self.text_format(message)
        extra = self._user_extra_dic.get(message.author.id, {})
        que = self.queue[message.guild.voice_client.session_id]
        que.put_nowait((text, speaker_id, extra))
        await que.play_queue()
    
    # vcから抜けたり入ったり別のvcに入ったとき呼ばれる
    @commands.Cog.listener(name='on_voice_state_update')
    async def on_voice_state_update(self, member: discord.Member, before, after):
        connecting_channelIDs = [v.channel.id for v in self.bot.voice_clients]
        text_channel = [m for i in self._channelIDs if (m := member.guild.get_channel(i))][0]
        if after.channel is None and before.channel.id in connecting_channelIDs: #VCから離脱
            voice_client = [v for v in self.bot.voice_clients if v.channel.id == before.channel.id][0]
            if not member.bot:
                members = [m for m in before.channel.members if not m.bot]
                if 0 == len(members):
                    await voice_client.disconnect(), await self.bot.sendEmbed(None, "誰もいなくなったので退出しました", sendTo=text_channel)
        elif before.channel is None and after.channel.id in connecting_channelIDs: #VCに参加
            voice_client = [v for v in self.bot.voice_clients if v.channel.id == after.channel.id][0]
            if member.bot and member.id == self.bot.user.id: #参加したのが自分
                self.queue[voice_client.session_id] = AudioQueue(self, voice_client)
            elif not member.bot:
                self.voicevox.ready(self.user_voice(member.id, member.guild.id))

    def user_voice(self, user_id: int, guild_id: int, out: bool = False) -> int:
        flag = False
        user_id = str(user_id)
        if guild_id not in self._user_voice_dic.keys():
            self._user_voice_dic[guild_id] = utils.FileUtil.read_by_guild(guild_id)
        if user_id not in self._user_voice_dic[guild_id].keys():
            self.set_user_voice(user_id, guild_id)
            flag = True
        if out:
            return self._user_voice_dic[guild_id][user_id], flag
        return self._user_voice_dic[guild_id][user_id]

    def set_user_voice(self, user_id: int, guild_id: int, val: int = -1) -> None:
        user_id = str(user_id)
        if guild_id not in self._user_voice_dic.keys():
            self._user_voice_dic[guild_id] = utils.FileUtil.read_by_guild(guild_id)
        
        if val < 0:
            name = random.choice(list(self.speakers.keys()))
            style = list(self.speakers[name].keys())[0]
            val = self.speakers[name][style]
        
        self._user_voice_dic[guild_id][user_id] = val
        utils.FileUtil.save_by_guild(self._user_voice_dic[guild_id], guild_id)

    def text_format(self, message: discord.Message) -> str:
        res = message.content
        replaces = {
            'ユーアールエル': r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)",
            'エモジ': r"\<\:.*\>",
            'メンション': r"\<\@\d*\>",
        }
        match = re.search(r"(\D)\1{4,}", res) # 5文字以上の文字の繰り返しは4文字にする
        if match:
            res = res.replace(match.group(0),match.group(0)[:4])
        for new, pat in replaces.items():
            res = re.sub(pat, new, res)
        eng = re.findall(r'[a-zA-Z]*',res)
        for e in eng:
            new = alkana.get_kana(e)
            if e and new:
                res = res.replace(e, new)
        dic = utils.FileUtil.read_by_guild(message.guild.id).get('Dictionary',{})
        for k, v in dic.items():
            res = res.replace(k,v)
        return res

class DictCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name='dictionary', aliases=['dic','d','dict'])
    async def dictionary(self, ctx: Context):
        return
    
    @dictionary.command(name='help')
    async def help(self, ctx: Context):
        embed = discord.Embed(
            title="Dictionary Help",
            color=discord.Colour.gold(),
            description=f'単語と読みを追加できます'
        )
        embed.add_field(name=f'/dictionary add <単語> <読み> または /d add <単語> <読み>',value='辞書に単語と読みを追加します',inline=False)
        embed.add_field(name=f'/dictionary remove <単語> または /d remove <単語>', value='辞書から単語を削除します',inline=False)
        embed.add_field(name=f'/dictionary modify <単語> <読み> または /d modify <単語> <読み>',value='単語の読みを置き換えます',inline=False)
        return await ctx.channel.send(embed=embed)

    @dictionary.command(
        name='add',
        option=[
            {
                "name": "target_word",
                "required": True
            },
            {
                "name": "replace_word",
                "required": True
            }
        ]
    )
    async def add(self, ctx: Context, target_word:str, replace_word:str):
        dic = await self.getDict(ctx.guild.id)
        dic[target_word] = replace_word
        await self.putDict(ctx.guild.id, dic)
        return await self.bot.sendEmbed(ctx, f"以下を辞書に登録しました。\n`{target_word}=>{replace_word}`")
    
    @dictionary.command(
        name='modify',
        option=[
            {
                "name": "target_word",
                "required": True
            },
            {
                "name": "replace_word",
                "required": True
            }
        ]
    )
    async def modify(self, ctx: Context, target_word:str, replace_word:str):
        dic = await self.getDict(ctx.guild.id)
        if target_word not in dic.keys():
            return await self.bot.sendEmbed(ctx, f"{target_word}は辞書に登録されていません。")
        dic[target_word] = replace_word
        await self.putDict(ctx.guild.id, dic)
        return await self.bot.sendEmbed(ctx, f"以下を辞書に登録しました。\n`{target_word}=>{replace_word}`")

    @dictionary.command(
        name='remove',
        option=[
            {
                "name": "target_word",
                "required": True
            }
        ]
    )
    async def remove(self, ctx: Context, target_word:str):
        dic = await self.getDict(ctx.guild.id)
        if target_word not in dic.keys():
            return await self.bot.sendEmbed(ctx, f"{target_word}は辞書に登録されていません。")
        past = dic.pop(target_word)
        await self.putDict(ctx.guild.id, dic)
        return await self.bot.sendEmbed(ctx, f"以下を辞書から削除しました。\n`{target_word}=>{past}`")

    async def putDict(self, guild_id:int, dic_data:Dict) -> None:
        data = utils.FileUtil.read_by_guild(guild_id)
        data['Dictionary'] = dic_data
        utils.FileUtil.save_by_guild(data, guild_id)
    
    async def getDict(self, guild_id:int) -> Dict:
        return utils.FileUtil.read_by_guild(guild_id).get('Dictionary',{})

async def setup(bot):
    await bot.add_cog(DictCog(bot))
    await bot.add_cog(TTSCog(bot))