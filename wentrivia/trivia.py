"""
Module for premade trivia configurations.

Trivia games can be created with any of the trivia classe in this module,
passing it at least a discord.py context object. They do not count with locking
mechanisms to make sure there's a single game per channel, it only handles the
game's internal logic.

Example:

>>> game = RegularTrivia(ctx)
>>> await game.start()
"""

import wentrivia.abc_trivia as abct


class RegularTrivia(
        abct.RegularLogicMixin,
        abct.ForgivingCheckerMixin,
        abct.JSONLoaderMixin
        ):
    pass
