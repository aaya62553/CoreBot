import discord
from discord.ext import commands ,tasks
from discord.ui import Select, View,Modal,TextInput,Button
import asyncio
import re
from dotenv import load_dotenv 
import os
from savedropbox_config import savedropboxconfig,refresh_access_token,loadconfig_dropbox
from keep_alive import keep_alive
import json
load_dotenv()



intents = discord.Intents.default()
intents.message_content = True
intents.members=True 
bot = commands.Bot(command_prefix="+", intents=intents,help_command=None)


help_cmd_page={

    "Moderation":{"admin <pseudo> ":"Permet d'avoir l'accès au bot",
                  "adminlist":"Permet d'afficher la liste des propriétaires du bot",
                  "unadmin <pseudo>":" Permet de retirer les permissions de propriétaire à un utilisateur",
                  "ban <pseudo>":" Permet de bannir un utilisateur",
                  "unban <id>":" Permet de débannir un utilisateur",
                  "kick <pseudo>":"Permet de kick un utilisateur",
                  "banlist":"Permet d'afficher la liste des utilisateurs bannis",
                  "derank <pseudo,role>":"Permet de retirer un role à un utilisateur",
                  "addrole <pseudo,role>":"Permet d'ajouter un role à un utilisateur",
                  "giveowner <pseudo>": "Permet de transferrer la propriété du bot à un administrateur",
                  "clear <nombre>":"Permet de supprimer un certain nombre de messages",
                  "lock":"Permet de verouiller un salon textuel",
                  "unlock":"Permet de déverouiller un salon textuel",
                  },
    "Gestion du serveur":{
                         "autoreact add <salon,emoji>":"Permet d'ajouter une réaction automatique à un salon",
                         "autoreact del <salon,emoji>":"Permet de retirer une réaction automatique à un salon",
                         "list autoreact":"Permet d'afficher la liste des salons avec réactions automatiques",
                         "massiverole <role>":"Permet d'ajouter un role à tous les membres du serveur",
                         "autorole <role>":"Ajoute automatiquement le role aux nouveaux arrivants",
                         "set joinchannel <salon>":"Permet de définir le salon de bienvenue",
                         "renew":"Permet de supprimer et remettre un salon",
                         "set botname <nom>":"Permet de changer le nom du bot",
                         "set theme <couleur hex>":"Permet de changer la couleur du bot",
                         "rename <pseudo> <new_name>":"Permet de renommer un utilisateur",
    },
    "Ticket":{"ticket_init":"Permet d'initialiser la création de ticket (executer dans le salon ticket)",
              "close":"Permet de fermer un ticket",
              "rename ticket <new_name>" : "Permet de renommer un ticket",
              "set ticketchannel <salon>" :"Permet de définir le salon de ticket",
              "set ticketcategory <category name>":" Permet de définir une catégorie de ticket",
              "add ticketform <category name>" :"Permet d'ajouter une question au formulaire de la categorie du ticket",
              "remove ticketcategory <category name>":"Permet de retirer une catégorie de ticket",
              "remove ticketform <category name>":" Permet de retirer un formulaire de ticket",
              "list ticketcategory":"Permet d'afficher la liste des catégories de ticket",
              "set ticketrole <role>":"Permet de définir le role ayant accès aux tickets",
              "set ticketimg <url de l'image>":"Permet de définir l'image du ticket",
             },
    "Logs":{"boostlog on <salon>":"Permet de définir les logs de boost",
            "boostlog off":"Permet de désactiver les logs de boost",
            "raidlog on <salon>":"Permet de définir les logs de raid",
            "raidlog off":"Permet de désactiver les logs de raid",
            "antilink <on/off>":"Permet d'activer/désactiver l'envoi de lien",
            "antiraid <on/off>":"Permet de kick les utilisateurs ajoutant un bot sans autorisation",
            "msglog on <salon>":"Permet de définir les logs de message",
            "msglog off":"Permet de désactiver les logs de message",
    },
    "Informations":{"server info":"Permet d'afficher les informations du serveur",
                    "server roles":"Permet d'afficher les roles du serveur",
                    "server pic":"Permet d'afficher l'icône du serveur",
                    "server banner":"Permet d'afficher la bannière du serveur",
                    "pic <pseudo>":"Permet d'afficher la photo de profil d'un utilisateur",
                    "banner <pseudo>":"Permet d'afficher la bannière d'un utilisateur",
    },

}

def loadconfig():
    with open('config.json','r') as f:
        config=json.load(f)
    return config
config=loadconfig()

def save_config():
  with open("config.json","w") as f:
     json.dump(config,f,indent=4)
  savedropboxconfig()



@bot.event
async def on_guild_join(guild):
    async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add):
        if entry.target.id == bot.user.id:
            inviter_id = entry.user.id
            break
    if str(guild.id) not in config["guilds"]:

      config["guilds"][str(guild.id)]={
       "owner_id":inviter_id,
       "admin_list":[inviter_id],
        "autorole":None,
        "welcome_channel":None,
        "antilink":False,
        "autoreact":{},
        "ticket":{"channel":None,"categories":{}},
        "logs":{},
        "theme":"ff0000"
 }
    save_config()
    await guild.system_channel.send("Utiliser +setup pour configurer le bot")




def get_admin_list(guild):
    return config["guilds"][str(guild.id)]["admin_list"]


def get_owner(guild):
    return config["guilds"][str(guild.id)]["owner_id"]




def generate_help_embeds(guild):
   embeds=[]
   for title in help_cmd_page:
      txt=""
      for commands in help_cmd_page[title]:
        txt+=f"**+{commands}**\n {help_cmd_page[title][commands]}\n\n"
      embed = discord.Embed(
            title=title,
            description=txt,
            color=int(config["guilds"][str(guild.id)]["theme"],16)
        )
      embeds.append(embed)
   return embeds


class PageView(View):
   def __init__(self,embeds):
      super().__init__(timeout=200)
      self.embeds=embeds
      self.current_page=0
 
   @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
   async def prev_page(self,interaction:discord.Interaction,button:Button):
      if self.current_page>0:
         self.current_page-=1
      elif self.current_page==0:
         self.current_page=len(self.embeds)-1
      await interaction.response.edit_message(embed=self.embeds[self.current_page],view=self)

   @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
   async def next_page(self,interaction:discord.Interaction,button:Button,):
      if self.current_page<len(self.embeds)-1:
         self.current_page+=1
      elif self.current_page==len(self.embeds)-1:
          self.current_page=0
      await interaction.response.edit_message(embed=self.embeds[self.current_page],view=self)
         
@bot.command()
async def help(ctx):
      embeds=generate_help_embeds(ctx.guild)
      view=PageView(embeds)
      await ctx.send(embed=embeds[0],view=view)
   
@bot.command()
async def giveowner(ctx,member:discord.Member):
   if ctx.author.id ==get_owner(ctx.guild) and member.id in get_admin_list(ctx.guild):
      config["guilds"][str(ctx.guild.id)]["owner_id"]=member.id
      save_config()
      await ctx.send(f'{member.mention} est maintenant le propriétaire du bot !')
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def autorole(ctx,role:discord.Role):
   if ctx.author.id == get_owner(ctx.guild):
      config["guilds"][str(ctx.guild.id)]["autorole"]=int(role.id)
      save_config()
      await ctx.send(f"Le role **{role.name}** sera automatiquement attribué aux nouveaux")
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def massiverole(ctx,role:discord.Role):
   if ctx.author.id==get_owner(ctx.guild):  
      for member in ctx.guild.members:
         if role not in member.roles:
            await member.add_roles(role)
      await ctx.send(f'Le role **{role.name}** a été ajouté à tous les membres du serveur')
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')




@bot.command()
async def admin(ctx,member):
    user_id = int(member.strip("<@!>"))
    if ctx.author.id==get_owner(ctx.guild) and user_id not in get_admin_list(ctx.guild):
      config["guilds"][str(ctx.guild.id)]["admin_list"].append(user_id)
      save_config()
      await ctx.send(f'{member} est maintenant un administrateur du bot !')
    else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def unadmin(ctx,member):
    user_id = int(member.strip("<@!>"))
    if ctx.author.id==get_owner(ctx.guild) and user_id in get_admin_list(ctx.guild):
          config["guilds"][str(ctx.guild.id)]["admin_list"].remove(user_id)
          save_config()

          await ctx.send(f'{member} n\'est plus un administrateur du bot !')
    else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def adminlist(ctx):
      admin_list=get_admin_list(ctx.guild)
      if ctx.author.id in admin_list:
        txt=""
        for admin in admin_list:
            txt+=f'● <@{admin}>\n'
        embed = discord.Embed(
          title='Liste des administrateurs',
          description=txt,
          color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
      )
        await ctx.send(embed=embed)
      else:
        await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')



@bot.command()
async def clear(ctx,limit=1):
      if ctx.author.id in get_admin_list(ctx.guild):
        await ctx.channel.purge(limit=limit+1)
      else:
         await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def ban(ctx,member:discord.Member,reason=None):
  admin_list=get_admin_list(ctx.guild)
  if ctx.author.id in admin_list and member.id not in admin_list and member.id!=ctx.author.id:
     await member.ban(reason=reason)
     await ctx.send(f'{member.mention} a été **banni**')
  else:
    await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def unban(ctx, user_id: str, *, reason=None):
    user_id = int(user_id.strip("<@!>"))
    if ctx.author.id in get_admin_list(ctx.guild):
      user = await bot.fetch_user(user_id)
      if user is None:
          await ctx.send("Utilisateur non trouvé.")
          return
      await ctx.guild.unban(user, reason=reason)
      await ctx.send(f'Utilisateur {user.mention} a été débanni')
    else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def banlist(ctx):
    if ctx.author.id in get_admin_list(ctx.guild):
      ban_list=[]
      async for bans in ctx.guild.bans():
        ban_list.append(bans.user)
      txt=""
      for entry in ban_list:
         txt+=f'● <@{entry.id}>\n'
      embed = discord.Embed(
          title='Liste des bannis',
          description=txt,
          color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
      )
      await ctx.send(embed=embed)

@bot.command()
async def kick(ctx,member:discord.Member,reason=None):
  if ctx.author.id in get_admin_list(ctx.guild):
    await member.kick(reason=reason)
    await ctx.send(f'{member.mention} a été **kick**')
  else:
    await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def pic(ctx,member:discord.Member=None):
    if member is None:
       member=ctx.author
    avatar_url = member.display_avatar.url
    embed = discord.Embed(title=f"Photo de profil de {member.name}", color=int(config["guilds"][str(ctx.guild.id)]["theme"],16))
    embed.set_image(url=avatar_url)
    await ctx.send(embed=embed)

@bot.command()
async def banner(ctx,member:discord.Member=None):
    if member is None:
       member=ctx.author
    user = await bot.fetch_user(member.id)
    if user.banner:
        banner_url = user.banner.url
        embed = discord.Embed(
            title=f"Bannière de {user.name}", 
            color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
        )
        embed.set_image(url=banner_url)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"{user.name} n'a pas de bannière définie.")

@bot.command()
async def server(ctx,arg):
   if arg=="info":
      embed = discord.Embed(
          title=ctx.guild.name,
          description=f"👑 Propriétaire : {ctx.guild.owner.mention}\n👥 Membres : {ctx.guild.member_count}\n📅 Création : {ctx.guild.created_at.strftime('%d/%m/%Y')}",
          color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
      )
      embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
      await ctx.send(embed=embed)
   elif arg=="roles":
      txt=""
      for role in ctx.guild.roles:
          if role.name != "@everyone":
            txt+=f'**{role.name}**\n'
      embed = discord.Embed(
          title='Liste des roles',
          description=txt,
          color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
      )
      await ctx.send(embed=embed)
   elif arg=="pic":
      icon_url = ctx.guild.icon.url if ctx.guild.icon else None

      if icon_url:
        embed = discord.Embed(title=f"Icône du serveur {ctx.guild.name}", color=int(config["guilds"][str(ctx.guild.id)]["theme"],16))
        embed.set_image(url=icon_url)
        await ctx.send(embed=embed)
      else:
        await ctx.send("Ce serveur n'a pas d'icône définie.")
   elif arg=="banner":
      banner_url = ctx.guild.banner.url if ctx.guild.banner else None

      if banner_url:
        embed = discord.Embed(title=f"Bannière du serveur {ctx.guild.name}", color=int(config["guilds"][str(ctx.guild.id)]["theme"],16))
        embed.set_image(url=banner_url)
        await ctx.send(embed=embed)
      else:
        await ctx.send("Ce serveur n'a pas de bannière définie.")

@bot.command()
async def lock(ctx):
    if ctx.author.id in get_admin_list(ctx.guild):
      channel=ctx.channel
      overwrite=channel.overwrites_for(ctx.guild.default_role)
      overwrite.send_messages=False
      await channel.set_permissions(ctx.guild.default_role,overwrite=overwrite)
      await ctx.send(f'Le salon **{channel.name}** a été verouillé')
    else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def unlock(ctx):
  if ctx.author.id in get_admin_list(ctx.guild):
      channel=ctx.channel
      overwrite=channel.overwrites_for(ctx.guild.default_role)
      overwrite.send_messages=True
      await channel.set_permissions(ctx.guild.default_role,overwrite=overwrite)
      await ctx.send(f'Le salon **{channel.name}** a été déverouillé')
  else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def addrole(ctx,member:discord.Member,role:discord.Role):
  if ctx.author.id in get_admin_list(ctx.guild):
    await member.add_roles(role)
    await ctx.send(f'Le role **{role.name}** a été ajouté à **{member.name}**')
  else:
    await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')
    
@bot.command()
async def derank(ctx,member:discord.Member,role:discord.Role):
  if ctx.author.id in get_admin_list(ctx.guild):
    await member.remove_roles(role)
    await ctx.send(f'Le role **{role.name}** a été retiré à **{member.name}**')
  else:
    await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def renew(ctx):
  if ctx.author.id in get_admin_list(ctx.guild):
      await ctx.channel.delete()
      new_channel=await ctx.guild.create_text_channel(name=ctx.channel.name,
                                          position=ctx.channel.position,
                                          category=ctx.channel.category,
                                          overwrites=ctx.channel.overwrites)
      await asyncio.sleep(1)
      confirmation=await new_channel.send(f'{ctx.message.author.mention} Salon **{ctx.channel.name}** a été renouvelé !')
      await asyncio.sleep(4)
      await confirmation.delete()

      #Supprimer l'id du salon qui a été renouvelé dans la liste des salons à autoreact
      try:
        for channel_id in config["guilds"][str(ctx.guild.id)]["autoreact"].keys():
          if str(ctx.channel.id)==channel_id:
            config["guilds"][str(ctx.guild.id)]["autoreact"].pop(channel_id)
            save_config()
      except:
        pass
  else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')



url_pattern = re.compile(r'https?://\S+|www\.\S+|discord\.gg/\S+')
@bot.event
async def on_message(message):
   if message.author==bot.user:
      return
   if bot.user.mention in message.content:
        await message.channel.send('Mon préfixe est **+**, utilisez +help pour voir les commandes disponibles')
   if config["guilds"][str(message.guild.id)]["antilink"] and url_pattern.search(message.content) and message.author.id not in get_admin_list(message.guild):
      await message.delete()
      warning =await message.channel.send(f"{message.author.mention} Vous n'êtes pas autorisé à envoyer des liens ici !")
      await asyncio.sleep(3)
      await warning.delete()
   if str(message.channel.id) in config["guilds"][str(message.guild.id)]["autoreact"].keys():
      for emoji in config["guilds"][str(message.guild.id)]["autoreact"][str(message.channel.id)]:
          await message.add_reaction(emoji)
   if message.type == discord.MessageType.premium_guild_subscription:
      if "boostlog" in config["guilds"][str(message.guild.id)]["logs"].keys():
          channel=discord.utils.get(message.guild.channels,id=config["guilds"][str(message.guild.id)]["logs"]["boostlog"])
          embed=discord.Embed(
              title="Boost",
              description=f"{message.author.mention} a boosté le serveur !",
              color=int(config["guilds"][str(message.guild.id)]["theme"],16)
          )
          await channel.send(embed=embed)
   if message.mention_everyone:
      if "raidlog" in config["guilds"][str(message.guild.id)]["logs"].keys():
          channel=discord.utils.get(message.guild.channels,id=config["guilds"][str(message.guild.id)]["logs"]["raidlog"])
          embed=discord.Embed(
              title="Mention everyone",
              description=f"{message.author.mention} a mentionné everyone !",
              color=int(config["guilds"][str(message.guild.id)]["theme"],16)
              )
          await channel.send(embed=embed)
   await bot.process_commands(message)


@bot.command()
async def autoreact(ctx,status,channel:discord.TextChannel,emoji:str):
   if ctx.author.id in get_admin_list(ctx.guild):
      if emoji[0:2]!="<:":
          if status.lower()=="add":
            if str(channel.id) not in config["guilds"][str(ctx.guild.id)]["autoreact"].keys():
          
                config["guilds"][str(ctx.guild.id)]["autoreact"][str(channel.id)]=[emoji]
            else:
                if emoji not in config["guilds"][str(ctx.guild.id)]["autoreact"][str(channel.id)]:
                  config["guilds"][str(ctx.guild.id)]["autoreact"][str(channel.id)].append(emoji)  
              
            await ctx.send(f"Réaction automatique activée pour le salon {channel.mention} avec l'emoji {emoji}")
          elif status.lower()=="del":
              if config["guilds"][str(ctx.guild.id)]["autoreact"][str(channel.id)]:
                  if emoji in config["guilds"][str(ctx.guild.id)]["autoreact"][str(channel.id)]:
                    config["guilds"][str(ctx.guild.id)]["autoreact"][str(channel.id)].remove(emoji)
                    await ctx.send(f"Réaction automatique désactivée pour le salon {channel.mention} avec l'emoji {emoji}")
          save_config()
      else:
          await ctx.send("Veuillez entrer un emoji valide")
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def antilink(ctx,status):
   if ctx.author.id in get_admin_list(ctx.guild):
      if status.lower()=="on":
          config["guilds"][str(ctx.guild.id)]["antilink"]=True
          await ctx.send("L'antilink est activé")
      elif status.lower()=="off":
          config["guilds"][str(ctx.guild.id)]["antilink"]=False
          await ctx.send("L'antilink est désactivé")
      else:
         await ctx.send("Veuillez entrer une commande valide (on/off)")
      save_config()
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.event
async def on_member_join(member:discord.Member):
   if config["guilds"][str(member.guild.id)]["welcome_channel"]:
      embed=discord.Embed(
          title="Bienvenue !",
          description=f"👋 Bienvenue {member.mention} sur le serveur {member.guild.name} !",
          color=int(config["guilds"][str(member.guild.id)]["theme"],16)
      )
      await bot.get_channel(config["guilds"][str(member.guild.id)]["welcome_channel"]).send(embed=embed)
   role_id=config["guilds"][str(member.guild.id)]["autorole"]
   role=discord.utils.get(member.guild.roles,id=role_id)
   if role:
        await member.add_roles(role)
   if member.bot:
      
      await asyncio.sleep(1)
      async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
         if entry.target.id==member.id:
              if "raidlog" in config["guilds"][str(member.guild.id)]["logs"].keys():
                  channel=discord.utils.get(member.guild.channels,id=config["guilds"][str(member.guild.id)]["logs"]["raidlog"])
                  embed=discord.Embed(
                  title="Bot ajouté",
                  description=f"Le bot {member.mention} a été ajouté par {entry.user.mention} !",
                  color=int(config["guilds"][str(member.guild.id)]["theme"],16)
                )
                  await channel.send(embed=embed)
              if entry.user.id not in get_admin_list(member.guild) and config["guilds"][str(member.guild.id)]["antiraid"]:
                
                roles_list = [role for role in entry.user.roles if role.name != "@everyone"]
                for role in roles_list:
                   await entry.user.remove_roles(role)

                await member.guild.kick(entry.user, reason="Ajout non autorisé d'un bot.")
                await member.guild.kick(member, reason="Ajout non autorisé d'un bot.")
                await entry.user.send("Vous avez été kické pour avoir ajouté un bot sans autorisation.")
                await member.send("Vous avez été kické pour avoir été ajouté par un bot sans autorisation.")
                break
@bot.command()
async def set(ctx,param1:str,param2):
   if ctx.author.id in get_admin_list(ctx.guild):
      if param1=="joinchannel":
          param2=int(param2.strip("<#>"))
          param2=discord.utils.get(ctx.guild.channels,id=param2)
          config["guilds"][str(ctx.guild.id)]["welcome_channel"]=param2.id
          await ctx.send(f"Le salon de bienvenue a été défini sur {param2.mention}")
      elif param1=="ticketchannel":
          param2=int(param2.strip("<#>"))
          param2=discord.utils.get(ctx.guild.channels,id=param2)
          config["guilds"][str(ctx.guild.id)]["ticket"]["channel"]=param2.id
          await ctx.send(f"Le salon de ticket a été défini sur {param2.mention}") 
      elif param1=="ticketrole":
         param2=discord.utils.get(ctx.guild.roles,id=int(param2.strip("<@&>")))
         config["guilds"][str(ctx.guild.id)]["ticket"]["role"]=param2.id     
         await ctx.send(f"Le role de ticket a été défini sur {param2.mention}")
      elif param1=="botname":
         config["guilds"][str(ctx.guild.id)]["botname"]=param2
         await ctx.guild.me.edit(nick=param2)
         await ctx.send(f"Le nom du bot a été défini sur **{param2}**")
      elif param1=="theme":
          try :
             param2=param2.strip("#")
             int(param2,16)
             config["guilds"][str(ctx.guild.id)]["theme"]=param2
             await ctx.send(f"Le thème du serveur a été défini sur **{param2}**")
          except :
              await ctx.send("Veuillez entrer une couleur hexadécimale valide")

      elif param1=="ticketimg" :
        if url_pattern.search(param2):
          config["guilds"][str(ctx.guild.id)]["ticket"]["img"]=param2
          await ctx.send(f"L'image du ticket a été défini sur **{param2}**")
        else:
          await ctx.send("Veuillez entrer une url valide (en .png, .jpg, .jpeg)")
            
      save_config()
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def add(ctx,param1:str,category_name:str):
   if ctx.author.id in get_admin_list(ctx.guild):
      if param1=="ticketcategory":
          if category_name not in config["guilds"][str(ctx.guild.id)]["ticket"]["categories"].keys():
            config["guilds"][str(ctx.guild.id)]["ticket"]["categories"][category_name]=[]
            view=CategoryButton(category_name)
            await ctx.send(f"Cliquez sur le bouton pour configurer la catégorie **{category_name}**.", view=view)
          else:
            await ctx.send(f"La catégorie **{category_name}** existe déjà, supprimez la catégorie pour changer ses paramètres.")
      
      
      elif param1=="ticketform":
         if category_name in config["guilds"][str(ctx.guild.id)]["ticket"]["categories"].keys():
            config["guilds"][str(ctx.guild.id)]["ticket"]["categories"][category_name]["form"]={}
            view=QuestionButton(category_name)
            await ctx.send(f"Cliquez sur le bouton pour ajouter une question au formulaire de la catégorie **{category_name}**.", view=view)
   
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def remove(ctx,param1:str,param2):
   if ctx.author.id in get_admin_list(ctx.guild):
      if param1=="ticketcategory":
          config["guilds"][str(ctx.guild.id)]["ticket"]["categories"].pop(param2)
          category = discord.utils.get(ctx.guild.categories, name=param2.upper())
          if category:
            for channel in category.channels:
              await channel.delete()
            await category.delete()
          await ctx.send(f"La catégorie **{param2}** a été retirée")
      elif param1=="ticketform":
          config["guilds"][str(ctx.guild.id)]["ticket"]["categories"][param2].pop("form")
          await ctx.send(f"Le formulaire de la catégorie **{param2}** a été retiré")
      save_config()

@bot.command()
async def list(ctx,param1:str):
    if ctx.author.id in get_admin_list(ctx.guild):
        if param1=="ticketcategory":
          categories=config["guilds"][str(ctx.guild.id)]["ticket"]["categories"]
          txt=""
          for category in categories:
              txt+=f'**{category}**\n'
          embed = discord.Embed(
            title='Liste des catégories de tickets',
            description=txt,
            color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
            )
          await ctx.send(embed=embed)
        elif param1=="autoreact":
          autoreact=config["guilds"][str(ctx.guild.id)]["autoreact"]
          txt=""
          for channel in autoreact:
              channel=discord.utils.get(ctx.guild.channels,id=int(channel))
              if channel and len(autoreact[str(channel.id)])>0:
                txt+=f'**{channel.mention}** : {" ".join(autoreact[str(channel.id)])}\n'
          embed = discord.Embed(
            title='Liste des salons avec réactions automatiques',
            description=txt,
            color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
            )
          await ctx.send(embed=embed)
        
    else:
        await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

#AJOUTER UNE QUESTION AU FORMULAIRE DE TICKET
class AddQuestion(Modal):
   def __init__(self,category_name:str):
      super().__init__(title="Ajouter une question")
      self.category_name=category_name
      self.question=TextInput(label="❓Question",placeholder="Entrez la question (ex: Pseudo et âge), utilisez des emojis pour plus de clarté")
      self.placeholder=TextInput(label="👀Placeholder/Exemple de réponse",placeholder="Entrez le placeholder")
      self.add_item(self.question)
      self.add_item(self.placeholder)
   async def on_submit(self, interaction: discord.Interaction):
      question=self.question.value
      placeholder=self.placeholder.value
      config["guilds"][str(interaction.guild.id)]["ticket"]["categories"][self.category_name]["form"][question]=placeholder
      save_config()
      await interaction.response.send_message(f"La question **{question}** a été ajoutée à la catégorie **{self.category_name}**", ephemeral=True)
      await interaction.response.send_message("Refaire la commande pour ajouter une autre question", ephemeral=True)
      recreate_ticket_view.start()

class QuestionButton(View):
   def __init__(self,category_name:str):
      super().__init__()
      self.category_name=category_name

   @discord.ui.button(label="Ajouter une question",style=discord.ButtonStyle.primary)
   async def configure_category(self,interaction:discord.Interaction,button:Button):
      modal=AddQuestion(self.category_name)
      await interaction.response.send_modal(modal)



#AJOUTER UNE CATEGORIE AUX TICKETS
class AddCategory(Modal):
    def __init__(self,category_name):
        super().__init__(title="Personnaliser la catégorie")
        self.category_name = category_name
        self.description = TextInput(label="📄 Description", default="Cliquez ici pour ouvrir un ticket")
        self.emoji = TextInput(label="🤪 Emoji", placeholder="Ajouter un emoji",required=False)
        self.add_item(self.description)
        self.add_item(self.emoji)
    async def on_submit(self, interaction: discord.Interaction):
       category_description=self.description.value
       category_emoji=self.emoji.value

       config["guilds"][str(interaction.guild.id)]["ticket"]["categories"][self.category_name] = {
            "description": category_description,
            "emoji": category_emoji
        }
       save_config()
       await interaction.guild.create_category(self.category_name.upper(),overwrites={interaction.guild.default_role:discord.PermissionOverwrite(read_messages=False)})
       await interaction.response.send_message(f"La catégorie **{self.category_name}** a été mise à jour avec la description et l'emoji.", ephemeral=True)

class CategoryButton(View):
   def __init__(self,category_name:str):
      super().__init__()
      self.category_name=category_name
   @discord.ui.button(label="Ajouter une catégorie",style=discord.ButtonStyle.primary)
   async def configure_category(self,interaction:discord.Interaction,button:Button):
      modal=AddCategory(self.category_name)
      await interaction.response.send_modal(modal)



class RecruitementFormModal(Modal):
    def __init__(self,interaction,category):
       super().__init__(title="Questionnaire")
       self.category=category
       for question,placeholder in config["guilds"][str(interaction.guild.id)]["ticket"]["categories"][category]["form"].items():
            text_input = TextInput(
                label=question,  # La question devient le label
                placeholder=placeholder,  # Placeholder pour guider l'utilisateur
                required=True  # Vous pouvez modifier ceci selon le besoin
            )
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        
        submit = {item.label:item.value for item in self.children}

        await create_ticket_channel(interaction, self.category, submit)


async def create_ticket_channel(interaction,category,submit=None):
        guild = interaction.guild
        member = interaction.user
        ticket_channel_name = f"{category}-{member.name}"


        if  discord.utils.get(guild.channels, name=ticket_channel_name):
            await member.send("Vous avez déjà un ticket ouvert.")
            return
        
        if "role" in config["guilds"][str(guild.id)]["ticket"].keys() and discord.utils.get(guild.roles,id=config["guilds"][str(guild.id)]["ticket"]["role"]) is not None:
            ticket_role=discord.utils.get(guild.roles,id=config["guilds"][str(guild.id)]["ticket"]["role"])

            overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),  # Hide the channel from normal members
            member: discord.PermissionOverwrite(read_messages=True),  # Allow the creator to see the channel
            ticket_role: discord.PermissionOverwrite(send_messages=True,read_messages=True)  # Allow the ticket role to see the channel
        }
        else:
            overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),  # Hide the channel from normal members
            member: discord.PermissionOverwrite(read_messages=True),  # Allow the creator to see the channel
        }
            
        ticket_channel = await guild.create_text_channel(ticket_channel_name, overwrites=overwrites,category=discord.utils.get(guild.categories,name=category.upper()))

        if submit:
            description = "\n".join([f"**{q} :**\n\n {a}\n" for q, a in submit.items()])
            embed = discord.Embed(title=f"Ticket de {member.name}", 
                                  description=description, 
                                  color=int(config["guilds"][str(guild.id)]["theme"],16)
                                  )
            if "img" in config["guilds"][str(guild.id)]["ticket"].keys():
              embed.set_image(url=config["guilds"][str(guild.id)]["ticket"]["img"])
            else:
              embed.set_image(url=r'https://4kwallpapers.com/images/walls/thumbs_3t/12504.png')
            await ticket_channel.send(embed=embed)
            await ticket_channel.send(f"Bonjour {member.mention}, votre ticket **{category}** a été crée.")
        else:
            await ticket_channel.send(f"Bonjour {member.mention}, votre ticket **{category}** a été crée. Décrivez votre problème et les administrateurs vous aideront.")        
        await interaction.response.send_message(f"Un ticket **{category}** ticket a été crée: {ticket_channel.mention}", ephemeral=True)

class TicketCategorySelect(Select):
    def __init__(self,guild):
        options=[]
        categories=config["guilds"][str(guild.id)]["ticket"]["categories"]
        for category in categories:
            try :
              options.append(discord.SelectOption(label=category, description=categories[category]["description"], emoji=categories[category]["emoji"] if categories[category]["emoji"]!="" else None))
            except :
               options.append(discord.SelectOption(label=category, description=categories[category]["description"]))
        super().__init__(placeholder="Choisir une catégorie pour votre ticket...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        if "form" in config["guilds"][str(interaction.guild.id)]["ticket"]["categories"][category].keys():
            await interaction.response.send_modal(RecruitementFormModal(interaction,category))
        else:
            await create_ticket_channel(interaction, category)
        await interaction.followup.edit_message(message_id=interaction.message.id, view=TicketView(interaction.guild))


class TicketView(View):
    def __init__(self,guild,timeout=86400):
        super().__init__(timeout=timeout)
        self.add_item(TicketCategorySelect(guild))

@tasks.loop(hours=24)
async def recreate_ticket_view():
    for guild in bot.guilds:
       if config["guilds"][str(guild.id)]["ticket"]["channel"] is not None:
          ticket_channel=discord.utils.get(guild.channels,id=config["guilds"][str(guild.id)]["ticket"]["channel"])
          await ticket_channel.purge(limit=10)
          embed = discord.Embed(
              title='Ticket System',
              description='Veuillez sélectionner une catégorie pour ouvrir votre ticket dans le menu déroulant ci-dessous.',
              color=int(config["guilds"][str(guild.id)]["theme"],16)
          )
          if "img" in config["guilds"][str(guild.id)]["ticket"].keys():
            embed.set_image(url=config["guilds"][str(guild.id)]["ticket"]["img"])
          else:
            embed.set_image(url=r'https://4kwallpapers.com/images/walls/thumbs_3t/12504.png')
          embed.set_footer(text='CoreBot Ticket')
          await ticket_channel.send(embed=embed,view=TicketView(guild))



@tasks.loop(hours=3)
async def update_config():
   new_droptoken=refresh_access_token(os.getenv("refresh_token"),os.getenv("APP_KEY"),os.getenv("APP_SECRET"))
   config['dropbox_token']=new_droptoken
   save_config()
@bot.event
async def on_ready():
    update_config.start()
    recreate_ticket_view.start()
    await bot.change_presence(activity=discord.Game(name="CoreBot"))
@bot.command()
async def ticket_init(ctx):
    if ctx.author.id in get_admin_list(ctx.guild):
      await ctx.message.delete()
      embed = discord.Embed(
          title='Ticket System',
          description='Veuillez sélectionner une catégorie pour ouvrir votre ticket dans le menu déroulant ci-dessous.',
          color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
      )
      if "img" in config["guilds"][str(ctx.guild.id)]["ticket"].keys():
        embed.set_image(url=config["guilds"][str(ctx.guild.id)]["ticket"]["img"])
      else:
        embed.set_image(url=r'https://4kwallpapers.com/images/walls/thumbs_3t/12504.png')
      embed.set_footer(text='CoreBot Ticket')
      await ctx.send(embed=embed, view=TicketView(ctx.guild))
    else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def close(ctx):
    """Command to close a ticket."""
    ticket_categories = config["guilds"][str(ctx.guild.id)]["ticket"]["categories"].keys()
    if any(ctx.channel.name.startswith(prefix.lower()) for prefix in ticket_categories):
        await ctx.send("Le ticket est en train d'être fermé...")
        await asyncio.sleep(2)
        await ctx.channel.delete()
    else:
        await ctx.send("Cette commande ne peut être utilisé que dans un canal de ticket.")

@bot.command()
async def rename(ctx,arg1,new_name):
    if ctx.author.id in get_admin_list(ctx.guild) :
      if arg1=="ticket":
        await ctx.channel.edit(name=new_name)
        await ctx.send(f"Le nom du ticket a été changé en **{new_name}**")
      elif discord.utils.get(ctx.guild.members,id=int(arg1.strip("<@!>"))):
        member=discord.utils.get(ctx.guild.members,id=int(arg1.strip("<@!>")))
        await member.edit(nick=new_name)
        await ctx.send(f"Le nom de {member.mention} a été changé en **{new_name}**")
    else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')


@bot.command()
async def boostlog(ctx,arg1,channel:discord.TextChannel=None):
   if ctx.author.id in get_admin_list(ctx.guild):
      if arg1=="on":
        config["guilds"][str(ctx.guild.id)]["logs"]["boostlog"]=channel.id
        await ctx.send(f"Les logs de boost ont été définis sur {channel.mention}")
      elif arg1=="off":
        config["guilds"][str(ctx.guild.id)]["logs"].pop("boostlog")
        await ctx.send("Les logs de boost ont été désactivés")
      save_config()
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def raidlog(ctx,arg1,channel:discord.TextChannel=None):
   if ctx.author.id in get_admin_list(ctx.guild):
      if arg1=="on":
        config["guilds"][str(ctx.guild.id)]["logs"]["raidlog"]=channel.id
        await ctx.send(f"Les logs de raid ont été définis sur {channel.mention}")
      elif arg1=="off":
        config["guilds"][str(ctx.guild.id)]["logs"].pop("raidlog")
        await ctx.send("Les logs de raid ont été désactivés")
      save_config()
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def antiraid(ctx,arg1):
    if ctx.author.id in get_admin_list(ctx.guild):
        if arg1=="on":
          config["guilds"][str(ctx.guild.id)]["antiraid"]=True
          await ctx.send("L'antiraid a été **activé**")
        elif arg1=="off":
          config["guilds"][str(ctx.guild.id)]["antiraid"]=False
          await ctx.send("L'antiraid a été **désactivé**")
        save_config()
    else:
        await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.command()
async def msglog(ctx,arg1,channel:discord.TextChannel=None):
   if ctx.author.id in get_admin_list(ctx.guild):
      if arg1=="on":
        config["guilds"][str(ctx.guild.id)]["logs"]["msglog"]=channel.id
        await ctx.send(f"Les logs de message ont été définis sur {channel.mention}")
      elif arg1=="off":
        config["guilds"][str(ctx.guild.id)]["logs"].pop("msglog")
        await ctx.send("Les logs de message ont été désactivés")
      save_config()
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')

@bot.event
async def on_message_delete(message):
    if "msglog" in config["guilds"][str(message.guild.id)]["logs"].keys():
      embed=discord.Embed(title=f"{message.author.name} Deleted a message", 
      description=message.content if message.content else "Message is empty or too long", 
      color=int(config["guilds"][str(message.guild.id)]["theme"],16)
      )
      channel=discord.utils.get(message.guild.channels, id=config["guilds"][str(message.guild.id)]["logs"]["msglog"])
      await channel.send(embed=embed)


@bot.command()
async def settings(ctx):
   if ctx.author.id in get_admin_list(ctx.guild):
      proprietaire=discord.utils.get(ctx.guild.members,id=config["guilds"][str(ctx.guild.id)]["owner_id"])
      txt=f"**Propriétaire du bot :** {proprietaire.mention}\n\n"
      join_role=discord.utils.get(ctx.guild.roles,id=config["guilds"][str(ctx.guild.id)]["autorole"])
      txt+=f"**Role d'arrivée :** {join_role.mention}\n\n"
      welcome_channel=discord.utils.get(ctx.guild.channels,id=config["guilds"][str(ctx.guild.id)]["welcome_channel"])
      if welcome_channel:
        txt+=f"**Salon de bienvenue :** {welcome_channel.mention}\n\n"
      if "channel" in config["guilds"][str(ctx.guild.id)]["ticket"].keys():
        ticket_channel=discord.utils.get(ctx.guild.channels,id=config["guilds"][str(ctx.guild.id)]["ticket"]["channel"])
        if ticket_channel:
          txt+=f"**Salon de ticket :** {ticket_channel.mention}\n\n"
      if "role" in config["guilds"][str(ctx.guild.id)]["ticket"].keys():
        ticket_role=discord.utils.get(ctx.guild.roles,id=config["guilds"][str(ctx.guild.id)]["ticket"]["role"])
        if ticket_role:
          txt+=f"**Role de ticket :** {ticket_role.mention}\n\n"
      antilink=config["guilds"][str(ctx.guild.id)]["antilink"]
      txt+=f"**Antilink :** {antilink}\n\n"
      if "antiraid" in config["guilds"][str(ctx.guild.id)].keys():
        antiraid=config["guilds"][str(ctx.guild.id)]["antiraid"]
        txt+=f"**Antiraid :** {antiraid}\n\n"
      embed=discord.Embed(
          title=f'Paramètres du serveur {ctx.guild.name}',
          description=txt,
          color=int(config["guilds"][str(ctx.guild.id)]["theme"],16)
      )
      embed.set_footer(text='CoreBot')
      await ctx.send(embed=embed)
   else:
      await ctx.send('Vous n\'avez pas les permissions nécessaires pour effectuer cette commande')




keep_alive()
bot.run(os.getenv("discord_TOKEN"))