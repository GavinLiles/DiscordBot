import discord
from slack import update_channel_map
import tomllib
import tomli_w
async def process_tml(message: discord.Message, SUPERADMINCHAT: str, SUPERADMINROLE: str, MentorRole: str):
    #This is used to loop through all attachments in a given message
    for attachment in message.attachments:

        #if the attachment is a toml file we should start reading it and extracting info to build out our new section of the discord
        if attachment.filename.endswith('.toml'):


            #This takes the toml file and reads it in as binary data then decodes it to a string
            toml_text = (await attachment.read()).decode("utf-8")

            #print the file its reading to the console for error checking can be removed later
            print(f"Received file: {attachment.filename}")


            #We should use trys and excepts for almost everything we do with this bot to determin errors quickly
            #This try block will attempt to parse the toml file and extract the classes and their names
            #If it fails it will print the error to the discord channel
            try:
                #parse the toml file and load it into a python dictionary
                data = tomllib.loads(toml_text)
                #Create a catagory for each class in the dict
                for cls in data["classes"]:
                    #check if the class name is already in use
                    existing = discord.utils.get(message.guild.categories, name=cls["name"])
                    #if it is we should not create a new category
                    #We should discuss what we are going to do in this situation further but for now it will just skip it
                    #update it replace merge it 
                    if not existing:
                        mentor = await message.guild.create_role(name=cls["name"] + " " + MentorRole, mentionable=True, color=discord.Color.orange())
                        user = await message.guild.create_role(name=cls["name"], mentionable=True, color=discord.Color.green())
                        #Create a new category for the class
                        NewCategory = await message.guild.create_category(cls["name"])
                        await NewCategory.set_permissions(mentor, read_messages=True, send_messages=True, connect=True, speak=True)
                        await NewCategory.set_permissions(user, read_messages=True, send_messages=True, connect=True, speak=True)
                        await NewCategory.set_permissions(message.guild.default_role, read_messages=False, connect=False)

                        HardChannels = ["General", "Sources", "GitHub", "Offtopic"]
                        for HardChannel in HardChannels:
                            #Create a new text channel for the class
                            new_channel = await message.guild.create_text_channel(HardChannel, category=NewCategory)
                            if HardChannel == "General":
                                general_channel_id = str(new_channel.id)
                                
                                # Grab Slack ID from TOML class entry if it exists
                                slack_id = cls.get("slack", "").strip()
                                
                                # If slack ID is present, write to channel_map.toml
                                if slack_id:
                                    update_channel_map(slack_id, general_channel_id)
                        admin = await message.guild.create_text_channel("Admin", category=NewCategory)
                        await admin.set_permissions(mentor, read_messages=True, send_messages=True, connect=True, speak=True)
                        await admin.set_permissions(user, read_messages=False, send_messages=False, connect=False, speak=False)
                        #Create a new voice channel for the class
                        await message.guild.create_voice_channel("General_1", category=NewCategory)
                        await message.guild.create_voice_channel("General_2", category=NewCategory)
                        #create an admin and a user role here
                    else:
                        await message.channel.send(f"The {cls} category alrady exists!!")
                        
                        
            except Exception as e:
                await message.channel.send(f"Error parsing TOML: {e}")