class TextStyle:
    DEFAULT = 0
    BOLD = 1


class TextColor:
    DEFAULT = 39
    LIGHT_GRAY = 37
    BLACK = 30
    LIGHT_MAGENTA = 95
    LIGHT_YELLOW = 93
    LIGHT_GREEN = 92
    LIGHT_CYAN = 96


class BackgroundColor:
    DEFAULT = 49
    RED = 41
    DARK_GRAY = 100
    LIGHT_GREEN = 102
    LIGHT_MAGENTA = 105
    LIGHT_CYAN = 106


def text_color_code(color):
    return '\033[{}m'.format(color)


def colored_text(color, text):
    default_color = text_color_code(TextColor.DEFAULT)
    return '{}{}{}'.format(text_color_code(color), text, default_color)


def colored_background(color, text):
    default_color = text_color_code(BackgroundColor.DEFAULT)
    return '{}{}{}'.format(text_color_code(color), text, default_color)


def colored_text_background(background_color, text_color, text):
    return colored_background(background_color, colored_text(text_color, text))


def bold_text(text):
    return '{}{}{}'.format(text_color_code(TextStyle.BOLD), text, text_color_code(TextStyle.DEFAULT))
