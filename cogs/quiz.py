import asyncio
import io
import json
import os
import random
import re
import time
from typing import Dict, List

import discord
import dotenv
import httpx
import jaconv
import numpy
import openai
from discord.ext import commands, tasks

dotenv.load_dotenv()


class QuizCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.http = httpx.AsyncClient()
        self.inGame: bool = False

        self.openai = openai.AsyncOpenAI(
            api_key=os.getenv("openai_api_key"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    @commands.command("ポケモン練習")
    async def pokemonCommand(self, ctx: commands.Context):
        if self.inGame:
            return

        await ctx.reply("練習を始めます")
        await self.pokemon(practice=True)

    @commands.command("クイズ練習")
    async def quizCommand(self, ctx: commands.Context, genre: str = ""):
        if self.inGame:
            return

        await ctx.reply("練習を始めます")
        await self.quiz(practice=True, genre=genre)

    @tasks.loop(minutes=5)
    async def quizLoop(self):
        await random.choice([self.quiz, self.pokemon])()

    @commands.Cog.listener()
    async def on_ready(self):
        self.quizLoop.start()

    async def pokemon(self, *, practice: bool = False):
        channel = self.bot.get_channel(1491704146544300094)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        self.inGame = True
        async with channel.typing():
            if not practice:
                coins = random.randint(1, 500)
            else:
                coins = 0

            response = await self.http.get(
                "https://pokeapi.co/api/v2/pokemon-species/?limit=0"
            )
            count = response.json()["count"]
            id = numpy.random.randint(1, count)

            print("count =", count)
            print("id =", id)

            response = await self.http.get(f"https://pokeapi.co/api/v2/pokemon/{id}")
            jsonData = response.json()

            imageUrl = jsonData["sprites"]["front_default"]

            response = await self.http.get(
                f"https://pokeapi.co/api/v2/pokemon-species/{id}/"
            )
            jsonData = response.json()

            name = next(
                entry["name"]
                for entry in jsonData["names"]
                if entry["language"]["name"] == "ja-hrkt"
            )

            response = await self.http.get(imageUrl)

            questionMessage = await channel.send(
                f"**問題！**\n\nこのポケモンは何？\n**20秒以内に回答してください**\n**最速正解で{coins}コインゲット**",
                file=discord.File(io.BytesIO(response.content), f"{id}.png"),
            )

        def check(message: discord.Message):
            if message.channel.id == channel.id:
                if (message.content == name) or (
                    jaconv.hira2kata(message.content) == name
                ):
                    return True
            return False

        try:
            message: discord.Message = await self.bot.wait_for(
                "message",
                timeout=20,
                check=check,
            )

            await questionMessage.reply(
                f"正解は**{name}**！\n正解者: {message.author.mention}\n**:coin: {coins}コインゲット！**"
            )

            if coins == 0:
                return

            guild = channel.guild

            commands = await guild.application_commands()

            for command in commands:
                if command.name == "transfer" and isinstance(
                    command, discord.SlashCommand
                ):
                    await command(channel, target=message.author, amount=coins)
                    break
        except asyncio.TimeoutError:
            await questionMessage.reply(
                f"正解は**{name}**！\n正解者: **なし！**"
            )
        finally:
            self.inGame = False

    async def quiz(self, *, practice: bool = False, genre: str = ""):
        channel = self.bot.get_channel(1491704146544300094)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        if not practice:
            coins = random.randint(1, 500)
        else:
            coins = 0

        self.inGame = True

        async with channel.typing():
            response = await self.openai.chat.completions.create(
                model="gemma-4-31b-it",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはクイズ出題AIです。JSONのみ返してください。",
                    },
                    {
                        "role": "user",
                        "content": (
                            "適当に◯✕クイズ1問だけ出してください。"
                            f"難しさ指数: {coins} / 500 で問題を作ってください。"
                            f"ジャンル指定: {genre if genre != '' else 'なし'} (ジャンル指定は無視しないでください。)"
                            "色んなジャンルから問題を出してください。"
                            "日常で使うクイズの他に「ボカロ」「ネットカルチャー」「ツイ廃」「アニメ」「日本史」「世界史」「性癖」「VTuber」など様々なジャンルで出題してください。(ぜひこれ以外のジャンルを出してほしい)"
                            '{"genre":"ジャンル","question":"問題文","answer":true/false,"explanation":"解説"}'
                            "json以外のデータを出力しないでください。(メッセージも)"
                        ),
                    },
                ],
            )

            rawText = (response.choices[0].message.content or "").strip()
            rawText = re.sub(r"^```json\s*", "", rawText, flags=re.I)
            rawText = re.sub(r"```$", "", rawText).strip()
            rawText = re.sub(r"<thought>.*?</thought>", "", rawText, flags=re.S).strip()

            match = re.search(r"\{.*\}", rawText, re.S)
            if not match:
                raise ValueError("JSON not found")

            print(match.group(0))
            data = json.loads(match.group(0))

            quizMessage = await channel.send(
                f"**ジャンル『{data['genre']}』からの問題！**\n\n{data['question']}\n\n"
                f"⭕ = ◯　❌ = ✕\n"
                f"制限時間: 20秒\n"
                f"**最速正解で{coins}コインゲット**"
            )

        await quizMessage.add_reaction("⭕")
        await quizMessage.add_reaction("❌")

        reactionLogs: Dict[int, List[str]] = {}
        firstTimes: Dict[int, float] = {}

        startTime = time.monotonic()

        def check(payload: discord.RawReactionActionEvent):
            return (
                payload.message_id == quizMessage.id
                and payload.user_id != self.bot.user.id  # ty:ignore[unresolved-attribute]
                and str(payload.emoji) in ["⭕", "❌"]
            )

        while True:
            remain = 20 - (time.monotonic() - startTime)

            if remain <= 0:
                break

            try:
                payload = await self.bot.wait_for(
                    "raw_reaction_add",
                    timeout=remain,
                    check=check,
                )

                userId = payload.user_id
                emoji = str(payload.emoji)

                if userId not in reactionLogs:
                    reactionLogs[userId] = []

                if emoji not in reactionLogs[userId]:
                    reactionLogs[userId].append(emoji)

                if userId not in firstTimes:
                    firstTimes[userId] = time.monotonic()

            except asyncio.TimeoutError:
                break

        guild = channel.guild

        bothUsers = []
        validUsers = []

        correctEmoji = "⭕" if data["answer"] else "❌"

        for userId, emojis in reactionLogs.items():
            member = guild.get_member(userId)

            # Bot / 自分 / 取得失敗 を除外
            if (
                member is None
                or member.bot
                or guild.me is not None
                and member.id == guild.me.id
            ):
                continue

            if "⭕" in emojis and "❌" in emojis:
                bothUsers.append(member)
                continue

            if correctEmoji in emojis:
                validUsers.append(member)

        validUsers.sort(key=lambda x: firstTimes[x.id])
        bothUsers.sort(key=lambda x: firstTimes[x.id])

        winner = validUsers[0] if validUsers else None

        messageText = (
            f"**時間終了！**\n"
            f"正解は {':o:' if data['answer'] else ':x:'}\n\n"
            f"**最速正解者**\n"
            f"{winner.mention if winner else '正解者なし'}"
        )

        if winner:
            messageText += f" **:coin: {coins}コインゲット！**"

        messageText += "\n\n"

        if bothUsers:
            exposeText = "\n".join(user.mention for user in bothUsers)
            messageText += f"**両方押し不正者晒し**\n{exposeText}\n\n"

        messageText += f"**解説**\n{data['explanation']}"

        await channel.send(messageText)

        self.inGame = False

        if winner is None:
            return

        if coins == 0:
            return

        commands = await guild.application_commands()

        for command in commands:
            if command.name == "transfer" and isinstance(command, discord.SlashCommand):
                await command(channel, target=winner, amount=coins)
                break


async def setup(bot: commands.Bot):
    await bot.add_cog(QuizCog(bot))
