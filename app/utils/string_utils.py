import random
import string


class StringUtils:
    @staticmethod
    def randomAlphaNumeric(length: int = 4) -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
