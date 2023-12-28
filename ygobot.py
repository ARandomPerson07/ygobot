import discord
import json
from discord.ext import commands
from discord import ActionRow, Button
from dotenv import load_dotenv
import os
import random
import psycopg2
import requests
from sentence_transformers import SentenceTransformer
from asyncio import TimeoutError
import time

class ygoview(discord.ui.View):
  def __init__(self):
    super().__init__()
    self.value = None

  # When the confirm button is pressed, set the inner value to `True` and
  # stop the View from listening to more input.
  # We also send the user an ephemeral message that we're confirming their choice.
  @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
  async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
    await interaction.response.send_message('Confirming', ephemeral=True)
    self.value = True
    self.stop()

  # This one is similar to the confirmation button except sets the inner value to `False`
  @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
  async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
    await interaction.response.send_message('Cancelling', ephemeral=True)
    self.value = False
    self.stop()

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

  #initialise db connection
  conn = psycopg2.connect(connection_string)
  print("connection established to db")
  
  #initialise dict for card frame colours
  frame_to_colour = {'effect' : discord.Color(0xFF8B53),
                     'normal' : discord.Color(0xFDE68A),
                     'spell' : discord.Color(0x1D9E74),
                     'trap' : discord.Color(0xBC5A84),
                     'synchro' : discord.Color(0xCCCCCC),
                     'xyz' : discord.Color(0x000000),
                     'fusion' : discord.Color(0xA086B7),
                     'link' : discord.Color(0x00008B),
                     'ritual' : discord.Color(0x9DB5CC),
                    }
  #initialise dict for specific cards with errors
  error_cards = {'Prediction Princess Tarotreith' : "flip",
                "Shinobaroness Peacock" : "spirit",
                "Shinobaron Peacock" : "spirit",
                "Shinobaron Shade Peacock" : "spirit",
                "Shinobaroness Shade Peacock" : "spirit",
                "Cyberse Sage" : "tuner",
                "Magikey Mechmusket - Batosbuster" : "tuner"}

  #initialise set of ED frames
  ed_frames = {'synchro','xyz','ritual','fusion','link'}

  #initialise set of abilities
  abilities = {'toon','spirit', 'union', 'gemini', 'flip'}

  #initialise the cid to gdrive link id dictionary
  with open('card_to_img.json') as f:
    card_to_img = json.load(f)

  print("Bot fully operational")
  
  # configure behaviour

  @client.event
  async def on_connect():
    print("Login successful. Initialising Bot...")

  @client.event
  async def on_ready():
    print("Spedbot is running, version of Dec 23,2023.")
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
  async def ygosearch(ctx: commands.Context, *, card_query):
    '''Search for a Yu-Gi-Oh! card using L2 similarity search on the
    card name's vectorized representation.'''
    await ctx.message.add_reaction("⌛")
    start = time.time()
    query_vec = model.encode(card_query)
    end = time.time()
    print(f"query embedded in {end - start}s")
    query_start = time.time()
    search_query = f"SELECT * FROM cards ORDER BY name_vector <-> '{query_vec.tolist()}' LIMIT 25;"
    try:
      with conn.cursor() as cur:
        cur.execute(search_query)
        responses = cur.fetchall()
    except:
        # reestablish db connection before retrying
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        cur.execute(search_query)
        responses = cur.fetchall()
    query_end = time.time()
    print(f"DB response received in {query_end - query_start}s")
    print(f"Full response generated in {query_end - start}s")
    # start of browsing loop
    # function to check for user response
    def check(message):
      return message.author == ctx.author and message.channel\
        == ctx.channel and ((message.content.isdigit() and 1 <=
                             int(message.content) <= 5) or
                            (message.content == 'c') or
                            (message.content == 'n') or
                            (message.content == 'p'))

    def get_embed_of_page_results(page):
      lookup_strings = []
      lookup_reply = discord.Embed(
          color=discord.Color(0xb92aab),
          title="Yu-Gi-Oh! Card Search",
          description=
          f'{ctx.author.display_name}, select the card you want to see details about using `1` to `5`, see the next/previous page of results using `n`/`p`, or cancel your query using `c`'
      )
      for index, response in enumerate(responses[page * 5:page * 5 + 5]):
        lookup_strings.append((f"**[ {str(index + 1)} ]** - {response[1]}"))
      lookup_reply.add_field(name="Results", value='\n'.join(lookup_strings))
      lookup_reply.add_field(name="Page", value=f'{page + 1}/5')
      return lookup_reply

    def get_card_info_embed(card_name : str):
      info_response = requests.get(
        f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={card_name}"
      )
      card_info = info_response.json()['data'][0]
      cid = card_info['id']
      gdrive_id = card_to_img[str(cid)]
      thumb_link = f'https://drive.google.com/uc?id={gdrive_id}'
      frame = card_info['frameType']
      if 'pendulum' in frame:
        #we have to handle pendulums differently due to double text boxes
        frame_colour = frame_to_colour[frame.split('_')[0]]
      else:
        #frame colour matches the embed colour
        frame_colour = frame_to_colour[frame]
        info_embed = discord.Embed(color = frame_colour, title = card_name, url = card_info['ygoprodeck_url'])
        info_embed.set_thumbnail(url = thumb_link)
        #monster case
        if 'monster' in card_info['type'].lower():
          #order is Type/ED Frame/Ability/Pendulum/Tuner/Effect
          card_types = card_info['type'].lower().split(" ")

          #error cards types corrections
          if card_name in error_cards.keys():
            card_types.append(error_cards[card_name])
          
          card_types = set(card_types)
          
          #add the race to the description string
          desc_string = card_info['race'] + '/'

          #add the ED Frame to the description string
          if len(card_types.intersection(ed_frames)) > 0:
            desc_string += card_types.intersection(ed_frames).pop().capitalize() + '/'

          #add the Ability
          if len(card_types.intersection(abilities)) > 0:
            desc_string += card_types.intersection(abilities).pop().capitalize() + '/'
        
          #check for Tuner
          if 'tuner' in card_types:
            desc_string += 'Tuner/'

          #remove the last /
          desc_string = desc_string[:-1]

          #card description text
          info_embed.description = desc_string

          card_stats = ''
          card_stats += f'**Attribute**: {card_info["attribute"]}\n'
          if 'link' not in card_types:
            card_stats += f'**Level/Rank**: {card_info["level"]}\n'
            card_stats += f'{card_info["atk"]} ATK/{card_info["def"]} DEF\n'
          else:
            card_stats += f'**Link Rating**: {card_info["linkval"]}\n'
            card_stats += f'**Link Arrows**: {" ".join(card_info["linkmarkers"])}\n'
            card_stats += f'{card_info["atk"]} ATK'
          
          info_embed.add_field(name = "Card Stats", value = card_stats)
          info_embed.add_field(name = 'Description', value = card_info['desc'])
        
        #spell case
        elif 'spell' in card_info['type'].lower():
          info_embed.description = f'{card_info["race"]} {card_info["type"]}'
          info_embed.add_field(name = 'Description', value = card_info['desc'])

        #trap case
        elif 'trap' in card_info['type'].lower():
          info_embed.description = f'{card_info["race"]} {card_info["type"]}'
          info_embed.add_field(name = 'Description', value = card_info['desc'])

        return info_embed
        
        
    browsing_loop = True
    #first 5
    page = 0
    
    while browsing_loop:

      lookup_reply = get_embed_of_page_results(page)
      last_sent = await ctx.send(embed=lookup_reply)
      
      try:
        # Wait for the user to input a number between 1 and 5
        reply_message = await client.wait_for('message',
                                              check=check,
                                              timeout=30.0)
        if reply_message.content == 'n':
          page += 1
          if page > 4:
            page = 4
            await ctx.send("End of Results List")
            continue
        elif reply_message.content == 'p':
          page -= 1
          if page < 0:
            page = 0
            await ctx.send("You are on the first page")
            continue
        elif reply_message.content == 'c':
            await ctx.send("Request Cancelled.")
            browsing_loop = False
            break
        else:
          # Get the selected index (subtract 1 to get the correct index)
          selected_index = int(reply_message.content) - 1 + page * 5

          # Get further information based on the selected index
          selected_card_name = responses[selected_index][1]
          # ygoprodeck_response = requests.get(
          #     f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={selected_card_name}"
          # )
          # card_info = ygoprodeck_response.json()
          # card_desc = card_info['data'][0]['desc']

          # further_info = f"**{selected_card_name}**\n\n"
          # further_info += card_desc

          further_info = get_card_info_embed(selected_card_name)
          # Send the further information to the user
          await ctx.send(embed = further_info)
          break

      except TimeoutError:
        await ctx.send(
            f"{ctx.author.display_name}, you took too long to respond. Operation canceled."
        )
        browsing_loop = False
      except (ValueError, IndexError):
        await ctx.send(
            "Invalid input. Please provide a number between 1 and 5.")

  @client.command(name = 'ask')
  async def ask(ctx: commands.Context):
      """Asks the user a question to confirm something."""
      # We create the view and assign it to a variable so we can wait for it later.
      view = ygoview()
      await ctx.send('Do you want to continue?', view=view)
      # Wait for the View to stop listening for input...
      await view.wait()
      if view.value is None:
          print('Timed out...')
      elif view.value:
          print('Confirmed...')
      else:
          print('Cancelled...')
  # run here
  client.run(os.environ['DISCORD_TOKEN'])
