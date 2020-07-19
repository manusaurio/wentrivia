"""
Main module for trivia games.

Trivia games can be created with the `Trivia` class, passing it a discord.py
context object as the first argument. This module does not count with locking
mechanisms to make sure there's a single game per channel, it only handles the
game's internal logic.

Example:

>>> game = Trivia(ctx)
>>> game.play()
"""

import asyncio
from collections import defaultdict
from difflib import SequenceMatcher
from dataclasses import dataclass, field
import json
from operator import itemgetter
from pathlib import Path
import random
from typing import Tuple, DefaultDict, List, Union

from discord import User, Message
from discord.ext.commands import Context


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
    def __init__(self, ctx: Context, lang='') -> None:
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
        if isinstance(message, Message):
            answer = message.content.lower()
        else:
            answer = message.lower()

        # TODO: This should be somewhere else. It's being generated each time.
        correct_answers = (correct.lower() for correct in question.answers)

        if question.perfect:
            return answer in correct_answers

        return any(
            SequenceMatcher(a=answer, b=correct).quick_ratio() > 0.8
            for correct in correct_answers
        )

    def load_questions(self, lang='', k=2) -> None:
        """
        Loads questions and shuffles them, with an optional `lang` argument,
        from a file named `questions.{lang}.json`.
        """
        filename = (
            'questions' +
            (f'.{lang}.json' if lang else '.json')
        )

        # it might be wise to run this from an `Executor`, but the time
        # it blocks is negligible for now
        with open(Path(__file__).parent / filename) as file:
            questions = json.load(file)['questions']

        len_range = range(len(questions))
        number = min(len(questions), k)

        chosen_index = (
            random.sample(len_range, k=number)
            + random.choices(len_range, k=k-number)
        )

        self.questions_pool = [
            Question(**questions[n])
            for n in chosen_index
        ]

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
