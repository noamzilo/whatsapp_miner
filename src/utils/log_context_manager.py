from collections import deque
from typing import Dict


class LoggingContextHandler:
    """
    context handler, which holds a stack of all contexts added.
    the stack is needed in order to handle nested contexts
    """
    def __init__(self):
        self.attributes = deque([{}])  # thread-safe, init with dummy

    def add_context(self, **new_context_vars):
        old_context = self.attributes[0]
        new_context = {**old_context, **new_context_vars}
        self.attributes.appendleft(new_context)

    def get(self, key):
        return self.attributes[0].get(key)

    def get_current_context(self) -> Dict:
        return self.attributes[0]

    def remove_context(self):
        self.attributes.popleft()

    def __str__(self):
        return str(self.attributes)


logging_context_handler = LoggingContextHandler()
