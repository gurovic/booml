def contest_problem_label(index: int) -> str:
    """
    Convert a zero-based contest problem index to an Excel-style label.

    Examples:
      0 -> A
      25 -> Z
      26 -> AA
    """
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("index must be an integer")
    if index < 0:
        raise ValueError("index must be >= 0")

    label = []
    current = index
    while True:
        current, remainder = divmod(current, 26)
        label.append(chr(ord("A") + remainder))
        if current == 0:
            break
        current -= 1

    return "".join(reversed(label))
