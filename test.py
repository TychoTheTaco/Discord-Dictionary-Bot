import utils


if __name__ == '__main__':
    #message = '**__w*o*wza**'
    #active = utils.format(message)
    #print(active)

    message = '**this is some *strangely* formatted** string that is supposed to be pretty __long__ so it'
    utils.split_formatting(message)
    #split = utils.split(message, 30)
    #print(split)

    #utils.format_all(split)
