# Discord Dictionary Bot

A simple bot that can fetch definitions and post them in chat. If you are connected to a voice channel, the bot will also read out the definition to you.

## Usage
Default command prefix: `.`<br>

### Commands
**define**<br>
Usage: `define [-v] [-lang <language_code>] <word>`<br>
Prints the definition of a word in the current text channel and optionally reads it out for you.<br>
Aliases: `d`<br>
Options:<br>
`-v`: Read out the definition to the voice channel you are connected to, if any.<br>
`-lang <language_code>`: Specify the language to use for text-to-speech.<br>

**help**<br>
Usage: `help`<br>
Shows available commands.<br>
Aliases: `h`<br>

**lang**<br>
Usage: `lang [-v]`<br>
Shows the list of supported languages for text to speech.<br>
Aliases: `l`<br>

**next**<br>
Usage: `next`<br>
If the bot is currently reading out a definition, this will make it skip to the next one.<br>
Aliases: `n`<br>

**property**<br>
Usage: `property <scope> (list | set <key> <value> | del <key>)`<br>
Set or remove channel or server properties.<br>
Aliases: `p`<br>

**stop**<br>
Usage: `stop`<br>
Makes this bot stop talking and removes any queued definition requests.<br>
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
