"""
Draft module for Trivia games. Soon to be moved to a package and
some other things.
"""

import asyncio
from collections import defaultdict
import os
from difflib import SequenceMatcher
from dataclasses import dataclass, field
import json
from operator import itemgetter
from random import shuffle
from typing import List, Tuple, DefaultDict, Dict, Union

from discord import LoginFailure, Message, User
from discord.ext.commands import Context, Cog
from discord.ext import commands

__version__ = "0.0.1"


@dataclass
class Question:
    """
    This class describes a question with the following fields:

    - `content`: the question or hint to be shown.
    - `points`: how many points answering correctly grants.
    - `answers`: correct answers to the question.
    - `perfect`: if `True`, the answer will only be considered correct if it's
       a perfect match
    """
    content: str
    points: int
    answers: Tuple[str]
    perfect: bool = field(default=False)


class Trivia:
    """
    Class with the logic for a trivia game.

    Each game should spawn an indiviual `Trivia` instance. This allows having
    multiple games running at the same time.
    """
    def __init__(self, ctx: Context, lang: str = '') -> None:
        self.ctx = ctx
        self.playing = False
        self.questions_pool: List[Question] = []
        self.language = lang
        self.scores: DefaultDict[User, int] = defaultdict(int)

    async def __aenter__(self) -> 'Trivia':
        self.playing = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        self.scores.clear()
        self.playing = False

    @staticmethod
    def check_answer(message: Union[str, Message], question: Question) -> bool:
        """Checks if the given `answer` matches any correct answer to
        the `question`"""
        answer: str = (
            message.content
            if isinstance(message, Message)
            else message
        ).lower()

        # TODO: This should be somewhere else. It's being generated each time.
        correct_answers = (correct.lower() for correct in question.answers)

        if question.perfect:
            return answer in correct_answers

        return any(
            SequenceMatcher(a=answer, b=correct).quick_ratio() > 0.8
            for correct in correct_answers
        )

    def load_questions(self, lang: str = '') -> None:
        """
        Loads questions and shuffles them, with an optional `lang` argument,
        from a file named `questions.{lang}.json`.
        """
        # TODO: This function loads the entire file. I should add a way to load
        # them with a limit
        filename = (
            'questions' +
            (f'.{lang}.json' if lang else '.json')
        )

        # it might be wise to run this from an `Executor`, but the time
        # it blocks is negligible for now
        with open(filename) as file:
            questions_dict = json.load(file)['questions']

        self.questions_pool = [
            Question(**question)
            for question in questions_dict
        ]

        shuffle(self.questions_pool)

    async def play(self) -> None:
        """Game logic."""
        async with self:
            await self.ctx.send('Comenzando partida!')
            self.load_questions()
            for question in self.questions_pool:
                await self.ctx.send(question)
                try:
                    msg: Message = await self.ctx.bot.wait_for(
                        'message', timeout=15,
                        check=lambda msg: self.check_answer(msg, question)
                    )
                    self.scores[msg.author] += question.points
                    await self.ctx.send(f'{msg.author} acertó! +{question.points} puntos')
                except asyncio.TimeoutError:
                    await self.ctx.send('Nadie contestó')
            if self.scores:
                scores = sorted(
                    self.scores.items(),
                    key=itemgetter(1),
                    reverse=True
                )
                await self.ctx.send('\n'.join(f'{p.name}: {s} puntos' for p, s in scores))
            else:
                await self.ctx.send('Nadie acertó nada')


class TriviaCog(Cog):
    """This cog sets the rules to start a new game, supevising what channels
    can games be started in, and how many can be played concurrently."""
    def __init__(self, bot: commands.bot.Bot):
        self.bot = bot
        self.games: Dict[int, Trivia] = {}
        self.channels = [627959873329430570]

    @commands.command()
    async def start(self, ctx: Context) -> None:
        """Starts a new game in the current channel."""
        can_start = (
            ctx.channel.id in self.channels and
            ctx.channel.id not in self.games.keys()
        )

        if not can_start:
            return

        game = Trivia(ctx)
        self.games[ctx.channel.id] = game
        await game.play()
        del self.games[ctx.channel.id]


if __name__ == '__main__':
    bot = commands.Bot(command_prefix='!')
    bot.add_cog(TriviaCog(bot))

    token = os.environ.get('TRIVIA_BOT_TOKEN')

    if token is None:
        raise LoginFailure("TRIVIA_BOT_TOKEN hasn't been set!")

    bot.run(token)
