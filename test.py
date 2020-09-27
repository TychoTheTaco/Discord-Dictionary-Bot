
def split(message, split_size):
    messages = []
    while len(message) > 0:

        # Find closest space before 'split_size' limit
        if len(message) > split_size:
            space_index = split_size
            while message[space_index] != ' ':
                space_index -= 1
        else:
            space_index = len(message)

        # Add chunk to message list
        m = message[:space_index]
        messages.append(m)

        # Remove chunk from message
        message = message[space_index:]

    return messages

if __name__ == '__main__':
    text = 'This is a really long message that needs to somehow be split on spaces so that the text to speech synthesizer can process it correctly. It needs to be split into chunks preferably by sentences to there arent any weird pauses.'
    result = split(text, 40)
    for m in result:
        print(len(m), m)
