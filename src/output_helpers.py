import sys

from IPython.display import clear_output


class _PeriodicClearStdout:
    def __init__(self, stream, lines_per_clear=5):
        self.stream = stream
        self.lines_per_clear = lines_per_clear
        self.line_count = 0

    def write(self, text):
        self.stream.write(text)
        self.stream.flush()
        self.line_count += text.count("\n")
        if self.line_count >= self.lines_per_clear:
            clear_output(wait=True)
            self.line_count = 0
        return len(text)

    def flush(self):
        self.stream.flush()


def run_with_output_clear(function, *args, lines_per_clear=5, **kwargs):
    original_stdout = sys.stdout
    sys.stdout = _PeriodicClearStdout(original_stdout, lines_per_clear)
    try:
        return function(*args, **kwargs)
    finally:
        sys.stdout = original_stdout