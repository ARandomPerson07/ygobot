import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import random
import psycopg2
import requests
import json
from sentence_transformers import SentenceTransformer
from asyncio import TimeoutError


def run_bot():
    # read environment variables from .env
    load_dotenv()

    # initialise client with correct intents
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix='_', intents=intents)

    # initialise vars and model for ygo search
    connection_string = os.environ['DB_CONNECT']
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # configure behaviour

    @client.event
    async def on_connect():
        print("Login successful. Initialising Bot...")

    @client.event
    async def on_ready():
        print("Spedbot is running, version of Dec 20,2023.")
        await client.change_presence(status=discord.Status.online,
                                     activity=discord.Game("Something, Maybe?"))

    @client.command(name='roll')
    async def roll(ctx, *dice):
        results = []
        for item in dice:
            typedice = item.split('d')
            typedice = [x for x in typedice if x != '']
            print(typedice)
            typedice = [int(x) for x in typedice]
            if len(typedice) == 1:
                result = random.randint(1, int(typedice[0]))
                results.append(f'd{typedice[0]} = **{result}**')
            else:
                x = 0
                subresults = []
            while x < typedice[0]:
                subresults.append(random.randint(1, typedice[1]))
                x += 1
            str_sub = ", ".join([str(x) for x in subresults])
            results.append(
                f'{typedice[0]}d{typedice[1]} = [{str_sub}] = **{sum(subresults)}**')
        flat_results = "\n".join(results)
        await ctx.send(flat_results)

    @client.command(name='ygo')
    async def ygosearch(ctx, *, card_query):
        query_vec = model.encode(card_query)
        search_query = f"SELECT * FROM cards ORDER BY name_vector <-> '{query_vec.tolist()}' LIMIT 5;"
        with psycopg2.connect(connection_string) as conn:
            cur = conn.cursor()
            cur.execute(search_query)
            responses = cur.fetchall()
        lookup_reply = ''
        for index, response in enumerate(responses):
            lookup_reply += f"**[{str(index + 1)}]** - {response[1]}\n"
        lookup_reply += "Press c to cancel query"
        await ctx.send(lookup_reply)

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and ((message.content.isdigit() and 1 <= int(message.content) <= 5) or (message.content == 'c'))

        try:
            # Wait for the user to input a number between 1 and 5
            reply_message = await client.wait_for('message', check=check, timeout=30.0)

            if reply_message.content == 'c':
                await ctx.send("Request Cancelled.")
            else:
                # Get the selected index (subtract 1 to get the correct index)
                selected_index = int(reply_message.content) - 1

                # Get further information based on the selected index
                selected_card_name = responses[selected_index][1]
                ygoprodeck_response = requests.get(
                    f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={selected_card_name}")
                card_desc = ygoprodeck_response.json()['data'][0]['desc']

                further_info = f"**{selected_card_name}**\n\n"
                further_info += card_desc
                # Send the further information to the user
                await ctx.send(further_info)

        except TimeoutError:
            await ctx.send("You took too long to respond. Operation canceled.")
        except (ValueError, IndexError):
            await ctx.send("Invalid input. Please provide a number between 1 and 5.")

    # run here
    client.run(os.environ['DISCORD_TOKEN'])
