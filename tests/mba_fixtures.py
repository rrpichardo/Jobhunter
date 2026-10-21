"""Sample job wording for the user's real search: roles open to MBA students graduating in 2027."""

MBA_2027 = 'This role is open to MBA students graduating in spring 2027.'


def mba(text='Build billing products.'):
    """A description that says the role is meant for MBA graduates of 2027."""
    return f'{text} {MBA_2027}'
