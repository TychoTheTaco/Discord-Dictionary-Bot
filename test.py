
def split(string, split_size):
    pass

if __name__ == '__main__':
    text = 'This is a really long message that needs to be split on spaces so that the text to speech synthesizer can process it correctly. It needs to be split into chunks preferably by sentences to there arent any weird pauses.'
    result = split(text, 40)
    print(result)
