import asyncio
import random
import string

import discord

client = discord.Client()


async def main():
    while True:
        pomelo = "".join(random.choices(string.ascii_lowercase, k=4))
        flag = await client.check_pomelo_username(pomelo)
        if not flag:
            print(pomelo, "available")


if __name__ == "__main__":
    asyncio.run(main())
