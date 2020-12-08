# Discord Dictionary Bot

A simple bot that can fetch definitions and post them in chat. If you are connected to a voice channel, the bot will also read out the definition to you.

## Usage
Default command prefix: `.`<br>

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

**lang**<br>
Shows the list of supported languages for text to speech.<br>
Usage: `lang [-v]`<br>
`-v`: Verbose mode. Prints out all the languages in chat instead of posting a link.<br>
Aliases: `l`<br>

**next**<br>
If the bot is currently reading out a definition, this will make it skip to the next one.<br>
Usage: `next`<br>
Aliases: `n`<br>

**property**<br>
Set or remove channel or server properties.<br>
Usage: `property <scope> (list | set <key> <value> | del <key>)`<br>
`<scope>`: The scope of the property. Either 'global' for guild-specific properties or 'channel' for channel-specific properties. Channel-specific properties will override guild-specific properties.<br>
`list`: List all properties in the specified scope.<br>
`set <key> <value>`: Set the value of the property named `key` to `value`.<br>
`del <key>`: Removes the specified property.<br>
Aliases: `p`<br>

**stop**<br>
Makes this bot stop talking and removes any queued definition requests.<br>
Usage: `stop`<br>
Aliases: `s`<br>

## Screenshots
![test](https://github.com/TychoTheTaco/Discord-Dictionary-Bot/blob/master/media/taco.jpg)

## Libraries and APIs
The following libraries / APIs used by this bot require an API token to function. If you want to clone this repository, you will need to use your own API token for them.<br>

### Owlbot
[URL](https://owlbot.info/)<br>
This API is used to get word definitions.

### Google Cloud Text-to-Speech
[URL](https://cloud.google.com/text-to-speech)<br>
This library is used to generate realistic text-to-speech translations in multiple languages.

### Google Cloud Firestore
[URL](https://firebase.google.com/products/firestore)<br>
This library is used to store guild and channel specific properties that are customizable by the user.

### Credits
#### Dictionary icon
This icon was modified from the [original](https://thenounproject.com/term/dictionary/653775/).<br>
`dictionary by Oriol Sallés from the Noun Project`
