import asyncio

from ollama import AsyncClient, Client
from tqdm.asyncio import tqdm


def normalize(embedding: list[float]) -> list[float]:
    norm = sum([x**2 for x in embedding]) ** 0.5
    return [x / norm for x in embedding]


def sync_embed(text: str, model: str = "mxbai-embed-large") -> list[float]:
    response = Client().embeddings(prompt=text, model=model)
    return normalize(response.embedding)


async def process_single(
    text: str, client: AsyncClient, sem: asyncio.Semaphore
) -> list[float]:
    async with sem:
        response = await client.chat(
            model="llama3.2",
            messages=[
                {
                    "role": "system",
                    "content": "Translate the following text into English:",
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
        )
        translation = response.message.content.strip()
        emb_response = await client.embeddings(
            model="mxbai-embed-large", prompt=translation
        )
        embedding = normalize(emb_response.embedding)
        return embedding


async def process_texts(texts: list[str], max_concurrent: int = 2) -> list[list[float]]:
    """Process all texts with limited concurrency"""
    sem = asyncio.Semaphore(max_concurrent)
    client = AsyncClient()

    tasks = [process_single(text, client, sem) for text in texts]
    results = await tqdm.gather(*tasks, ascii=True, total=len(texts))

    return [r for r in results if not isinstance(r, Exception)]
