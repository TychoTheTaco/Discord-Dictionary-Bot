# Discord Dictionary Bot

<img src="https://github.com/TychoTheTaco/Discord-Dictionary-Bot/blob/master/media/dictionary.png?raw=true" width="64" align="left"></img>
A Discord bot that can fetch definitions and post them in chat. If you are connected to a voice channel, the bot can also read out the definition to you. Dictionary bot can also translate words and phrases to many different
languages! [Invite Dictionary Bot to your server!](https://discord.com/api/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands) Check out
the [website](https://ddd.bellers.dev) for more information.

## Usage

Please see the [website](https://prod.d3967euqdvu56b.amplifyapp.com) for a list of commands.

## Installation

### Requirements

Below is a list of APIs that are currently used by the bot. To run the bot yourself, you will need to provide your own API key for these services.

- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech)
- [Google Cloud Firestore](https://firebase.google.com/products/firestore)
- [Google Cloud BigQuery](https://cloud.google.com/bigquery)

Additionally, you will need [FFmpeg](https://ffmpeg.org/).

### Installation

To install, simply run `pip install .` in the project's root directory. You can then run the bot using `python -m discord_dictionary_bot` along with the appropriate arguments described below.

### Dictionary API's

This bot supports the following dictionary API's.

| Name | Description |
| --- | --- |
|`google`|[Unofficial Google Dictionary API](https://github.com/meetDeveloper/googleDictionaryAPI)|
|`owlbot`| [Owlbot](https://owlbot.info/)|
|`webster-collegiate`| [Merriam Webster Collegiate](https://dictionaryapi.com/products/api-collegiate-dictionary)|
|`webster-medical`| [Merriam Webster Medical](https://dictionaryapi.com/products/api-medical-dictionary)|
|`rapid-words`| [RapidAPI WordsAPI](https://www.wordsapi.com/)|

### Program Arguments

|Argument| Description |
| --- | --- |
|<code>&#8209;&#8209;discord&#8209;token&nbsp;\<token\></code>|Your discord bot token.|
|<code>&#8209;&#8209;google&#8209;credentials&#8209;path&nbsp;\<path\></code>| Path to the Google application credentials file.|
|<code>&#8209;&#8209;ffmpeg&#8209;path&nbsp;\<token\></code>| Path to the FFmpeg executable.|
|<code>&#8209;&#8209;dictionary&#8209;api&nbsp;\<apis\></code>| Determines which dictionary API's to use. Multiple API's can be specified by separating each API name with a comma. The bot will use them in the order provided. This is useful for when the preferred API fails.|
|<code>&#8209;&#8209;owlbot&#8209;api&#8209;token&nbsp;\<token\></code>| Your Owlbot API token. Only required if using the `owlbot` API.|
|<code>&#8209;&#8209;webster&#8209;collegiate&#8209;api&#8209;token&nbsp;\<token\></code>| Your Merriam Webster API token. Only required if using the `webster-collegiate` API.|
|<code>&#8209;&#8209;webster&#8209;medical&#8209;api&#8209;token&nbsp;\<token\></code>| Your Merriam Webster API token. Only required if using the `webster-medical` API.|
|<code>&#8209;&#8209;rapid&#8209;words&#8209;api&#8209;token&nbsp;\<token\></code>| Your RapidAPI WordsAPI token. Only required if using the `rapid-words` API.|

## Credits

#### Dictionary icon

<img src="https://github.com/TychoTheTaco/Discord-Dictionary-Bot/blob/master/media/dictionary.png?raw=true" width="64" align="left"></img>
This icon was modified from the [original](https://thenounproject.com/term/dictionary/653775/).<br>
`dictionary by Oriol Sallés from the Noun Project`
