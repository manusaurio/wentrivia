from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import json
from operator import itemgetter
from pathlib import Path
import random
import typing as t


from discord import User, Message  # type: ignore
from discord.ext.commands import Context  # type: ignore


@dataclass
class Question:
    """
    This class describes a question with the following fields:

    - `content`: the question or hint to be shown.
    - `points`: how many points answering correctly grants.
    - `answers`: correct answers to the question, to display.
    - `lowercase_answers`: correct answers in lowercase, to compare.
    """
    content: str = 'Not set'
    points: int = 0
    answers: t.Tuple[str, ...] = field(default_factory=tuple)
    lowercase_answers: t.Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.answers and not self.lowercase_answers:
            self.lowercase_answers = tuple(a.lower() for a in self.answers)


@dataclass
class ForgivingQuestion(Question):
    """
    A question that might not require a perfect answer to consider it valid.
    When set to true, `perfect` indicates that the answers must be a perfect
    match.
    """
    perfect: bool = False


class ABCTrivia(ABC):
    """Base class to combine with mixins and make Trivia games."""
    def __init__(
            self,
            ctx: Context,
            category='',
            factory: t.Callable[..., t.Any] = Question,
    ) -> None:
        self.ctx = ctx
        self.playing = False
        self.questions_pool: t.List[Question] = []
        self.category = category
        self.scores: t.DefaultDict[User, int] = defaultdict(int)
        self.factory = factory

    async def __aenter__(self) -> 'ABCTrivia':
        self.playing = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        self.playing = False

    @abstractmethod
    def check_answer(self, message: t.Any, question: t.Any) -> bool:
        """Checks if an answer is correct, comparing it to the question."""

    @abstractmethod
    def load_questions(self, *, category='', k=2) -> None:
        """Loads questions. Override to load them and refer to them in
        `self.questions_pool"""

    @abstractmethod
    async def start(self, *args, **kwargs):
        """Starts the game."""


class JSONLoaderMixin(ABCTrivia):
    def load_questions(self, *, category='', k=2) -> None:
        """
        Loads questions and shuffles them, with an optional `lang` argument,
        from a file named `questions.{lang}.json`.
        """
        filename = (
            'questions' +
            (f'.{category}.json' if category else '.json')
        )

        with open(Path(__file__).parent / filename) as file:
            questions = json.load(file)['questions']

        len_range = range(len(questions))
        number = min(len(questions), k)

        chosen_index = (
            random.sample(len_range, k=number)
            + random.choices(len_range, k=k-number)
        )

        self.questions_pool = [
            self.factory(**questions[n])
            for n in chosen_index
        ]


class ForgivingCheckerMixin(ABCTrivia):
    def __init__(self, forgiveness_ratio=0.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.factory = ForgivingQuestion
        self.__ratio = forgiveness_ratio

    def check_answer(
            self,
            message: t.Union[str, Message],
            question: ForgivingQuestion
    ) -> bool:
        """Checks if the given `answer` matches any correct answer to
        the `question`"""
        if isinstance(message, Message):
            answer = message.content.lower()
        else:
            answer = message.lower()

        correct_answers = question.lowercase_answers

        if question.perfect:
            return answer in correct_answers

        return any(
            SequenceMatcher(a=answer, b=correct).quick_ratio() > self.__ratio
            for correct in correct_answers
        )


class RegularLogicMixin(ABCTrivia):
    """
    Trivia mixin to have a regular competitive logic: only the first one who
    answers gets the points for a given question.
    """
    async def _play(self, **kwargs) -> None:  # type: ignore
        """Game logic."""
        async with self:
            self.load_questions(**kwargs)
            await self.ctx.send('Comenzando partida!')

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

    async def start(self, *args, **loader_kwargs) -> None:
        """Starts the game"""
        await self._play(**loader_kwargs)


class ForgivingTrivia(RegularLogicMixin, ForgivingCheckerMixin, JSONLoaderMixin):
    def __init__(self, ctx: Context):
        super().__init__(ctx=ctx)
