"""Generators to produce specific random strings and values from different distributions"""

import math
import random
import uuid
from datetime import datetime, timedelta
from typing import List


def pareto(x_m: float, alpha: float, rnd: random.Random) -> float:
    """Return a random number drawn from a Pareto distribution,

    Parameters
    ----------
    x_m : float
        Minimum value.
    alpha : float
        Power law exponent.
    rnd : random.Random
        Random number generator to use.

    Returns
    -------
    float
    """
    return x_m / (rnd.uniform(0.0, 1.0) ** (1.0 / alpha))


def poisson(rate: float, duration: float, rnd: random.Random) -> int:
    """Return a random number drawn from a Poisson distribution

    Uses the algorithm at:
    https://en.wikipedia.org/wiki/Poisson_distribution#Random_variate_generation

    Parameters
    ----------
    rate : float
        Rate that we expect things to occur at.
    duration : float
        Duration over which to find the number of occurences.
    rnd : random.Random
        Random number generator to use.

    Returns
    -------
    int
    """

    L = math.exp(-rate * duration)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p = p * rnd.uniform(0.0, 1.0)
    return k - 1


def uniform_dates(num: int, start_date: datetime, end_date: datetime, rnd: random.Random) -> List[datetime]:
    """Randomly generate a series of uniformly-distributed consequtive datetimes

    Parameters
    ----------
    num : int
        Number of dates to generate.
    start_date : datetime
        Start of datetime range.
    end_date : datetime
        End of datetime range.
    rnd : random.Random
        Random number generator.

    Returns
    -------
    List[datetime]
        List of datetimes.
    """
    duration = (end_date - start_date).days
    dates = [start_date + timedelta(days=rnd.uniform(0.0, duration)) for _ in range(num)]
    dates.sort()
    return dates


def uuid4(rnd: random.Random, prefix: str = "abcd1234") -> str:
    """Randomly generate a fake uuid4 that is clearly marked as fake

    Parameters
    ----------
    prefix : str, optional
        Optional prefix text to replace the first 8 digits of a uuid.

    Returns
    -------
    str
        uuid string
    """
    return prefix[:8] + str(uuid.UUID(int=rnd.getrandbits(128), version=4))[8:]


def org_id(locale: str, rnd: random.Random):
    """Randomly generate a fake org id.

    Parameters
    ----------
    locale : str
        Locale string in the format "en_GB".
    rnd : random.Random
        Random number generator.

    Returns
    -------
    str
        Fake org id string.
    """
    return (
        locale[3:]
        + "-"
        + "".join(rnd.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
        + "-"
        + "{:08d}".format(rnd.randint(0, 99999999))
    )
