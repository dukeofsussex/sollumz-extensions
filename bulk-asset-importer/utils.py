from enum import Enum
from sys import stdout

class Colour(Enum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    PURPLE = 35
    CYAN = 36
    WHITE = 37

class YTFHelperOperator:
    def __init__(self, importSettings):
        self.import_settings = importSettings

class ImportSettings:
    join_geometries = True

    import_as_asset = True

    split_by_bone = False

def colourise(message, colour):
    return f'\033[0;{colour.value}m{message}\033[0m'
