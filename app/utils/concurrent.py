import asyncio
from asyncio import Semaphore
from typing import Awaitable, List, Iterable, Callable


class AsyncTaskPool:
    def __init__(self, max_workers: int = 10):
        """

        Args:
            max_workers: 任务最大并发数
        """
        self.semaphore = Semaphore(max_workers)

    async def _run_task(self, task: Awaitable):
        async with self.semaphore:
            return await task

    async def run(self, tasks: List[Awaitable]):
        return await asyncio.gather(*[self._run_task(task) for task in tasks])

    async def map(self, fn: Callable[..., Awaitable], *iterables: Iterable):
        tasks = [fn(*args) for args in zip(*iterables)]
        return await self.run(tasks)


if __name__ == "__main__":

    async def test(x, y):
        await asyncio.sleep(1)
        print(x, y)
        return x + y

    result = asyncio.run(AsyncTaskPool(2).map(test, [1, 2, 3, 4], [5, 6, 7, 8]))
    print(result)
