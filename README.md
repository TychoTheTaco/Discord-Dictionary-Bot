# Discord Dictionary Bot
<img src="https://github.com/TychoTheTaco/Discord-Dictionary-Bot/blob/master/media/dictionary.png?raw=true" width="64" align="left"></img>
A simple bot that can fetch definitions and post them in chat. If you are connected to a voice channel, the bot will also read out the definition to you. [Invite Dictionary Bot to your server!](https://discord.com/api/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands)



## Usage
Default command prefix: `.`<br>This bot also supports [Slash Commands](https://discord.com/developers/docs/interactions/slash-commands). The syntax for slash commands is a little from the usage shown below, though mostly the same. The Discord UI provides usage hints for slash commands. Note that currently slash commands do not support aliases.<br>

### Commands
**define**<br>
Prints the definition of a word in the current text channel and optionally reads it out for you.<br>
Usage: `define [-v] [-lang <language_code>] <word>`<br>
`-v`: Read out the definition to the voice channel you are connected to, if any.<br>
`-lang <language_code>`: Specify the language to use for text-to-speech.<br>
`<word>`: The word to define.<br>
Aliases: `d`<br>

**help**<br>
Shows available commands.<br>
Usage: `help`<br>
Aliases: `h`<br>

**languages**<br>
Shows the list of supported languages for text to speech.<br>
Usage: `languages [-v]`<br>
`-v`: Verbose mode. Prints out all the languages in chat instead of posting a link.<br>
Aliases: `l`, `lang`<br>

**next**<br>
If the bot is currently reading out a definition, this will make it skip to the next one.<br>
Usage: `next`<br>
Aliases: `n`<br>

**property**<br>
Set or remove channel or server properties.<br>
Usage: `property <scope> (list | set <key> <value> | del <key>)`<br>
`<scope>`: The scope of the property. Either `global` for guild-specific properties or `channel` for channel-specific properties. Channel-specific properties will override guild-specific properties.<br>
`list`: List all properties in the specified scope.<br>
`set <key> <value>`: Set the value of the property named `key` to `value`.<br>
`del <key>`: Removes the specified property.<br>
Aliases: `p`<br>

**stop**<br>
Makes this bot stop talking and removes any queued definition requests.<br>
Usage: `stop`<br>
Aliases: `s`<br>

## Screenshots
![taco](https://github.com/TychoTheTaco/Discord-Dictionary-Bot/blob/master/media/taco.jpg)

## Installation

### Requirements
Below is a list of APIs that are currently used by the bot. To run the bot yourself, you will need to provide your own API key for these services.
- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech)
- [Google Cloud Firestore](https://firebase.google.com/products/firestore)
- [Google Cloud Logging](https://cloud.google.com/logging)
- [Google Cloud BigQuery](https://cloud.google.com/bigquery)

Additionally, you will need [FFmpeg](https://ffmpeg.org/).

### Installation
To install, simply run `pip install .` in the project's root directory. You can then run the bot using `python -m discord_dictionary_bot` along with the appropriate arguments described below.

### Dictionary API's
This bot supports the following dictionary API's.

| Name      | Description |
| --- | --- |
|`google`|[Unofficial Google Dictionary API](https://github.com/meetDeveloper/googleDictionaryAPI)|
|`owlbot`| [Owlbot](https://owlbot.info/)|
|`webster`| [Merriam Webster](https://dictionaryapi.com/)|
|`rapid-words`| [RapidAPI WordsAPI](https://www.wordsapi.com/)|

### Program Arguments
|Argument            | Description |
| --- | --- |
|`--discord-token <token>`|Your discord bot token.|
|`--google-credentials-path <path>`| Path to the Google application credentials file.|
|`--ffmpeg-path <token>`| Path to the FFmpeg executable.|
|`--dictionary-api <apis>`| Determines which dictionary API's to use. Multiple API's can be specified by separating each API name with a comma. The bot will use them in the order provided. This is useful for when the preferred API fails.|
|`--owlbot-api-token <token>`| Your Owlbot API token. Only required if using the `owlbot` API.|
|`--webster-api-token <token>`| Your Merriam Webster API token. Only required if using the `webster` API.|
|`--rapid-words-api-token <token>`| Your RapidAPI WordsAPI token. Only required if using the `rapid-words` API.|

## Credits
#### Dictionary icon
<img src="https://github.com/TychoTheTaco/Discord-Dictionary-Bot/blob/master/media/dictionary.png?raw=true" width="64" align="left"></img>
This icon was modified from the [original](https://thenounproject.com/term/dictionary/653775/).<br>
`dictionary by Oriol Sallés from the Noun Project`
