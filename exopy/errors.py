class ExopyError(Exception):
    """Base exception for all exopy binary parsing and level building errors."""


class WrongMagicError(ExopyError):
    def __init__(self, got: bytes = b""):
        super().__init__(f"Wrong magic number (expected b'NYA^', got {got!r})")


class InvalidDynamicTypeError(ExopyError):
    def __init__(self, value: int):
        self.value = value
        super().__init__(f"Invalid dynamic type: {value}")


class InvalidStaticTypeError(ExopyError):
    def __init__(self, value: int):
        self.value = value
        super().__init__(f"Invalid static type: {value}")


class InvalidObjectPropertyError(ExopyError):
    def __init__(self, value):
        self.value = value
        super().__init__(f"Invalid object property: {value!r}")


class InvalidOldActionTypeError(ExopyError):
    def __init__(self, value: int):
        self.value = value
        super().__init__(f"Invalid old action type: {value}")


class InvalidActionTypeError(ExopyError):
    def __init__(self, value: int):
        self.value = value
        super().__init__(f"Invalid action type: {value}")


class InvalidThemeError(ExopyError):
    def __init__(self, value: str):
        self.value = value
        super().__init__(f"Invalid theme: {value!r}")
