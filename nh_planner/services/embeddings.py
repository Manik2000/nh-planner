import asyncio

from ollama import AsyncClient, Client
from tqdm.asyncio import tqdm


class EmbeddingService:
    
    def __init__(self, db, chat_model="llama3.2", embed_model="mxbai-embed-large"):
        self.db = db
        self.chat_model = chat_model
        self.embed_model = embed_model

    @staticmethod
    def normalize(embedding: list[float]) -> list[float]:
        norm = sum([x**2 for x in embedding]) ** 0.5
        return [x / norm for x in embedding]

    def sync_embed(self, text: str) -> list[float]:
        response = Client().embeddings(prompt=text, model=self.embed_model)
        return self.normalize(response.embedding)

    async def process_single(
        self, text: str, client: AsyncClient, sem: asyncio.Semaphore
    ) -> list[float]:
        async with sem:
            response = await client.chat(
                model=self.chat_model,
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
                model=self.embed_model, prompt=translation
            )
            embedding = self.normalize(emb_response.embedding)
            return embedding

    async def process_texts(
        self, texts: list[str], max_concurrent: int = 2
    ) -> list[list[float]]:
        sem = asyncio.Semaphore(max_concurrent)
        client = AsyncClient()

        tasks = [self.process_single(text, client, sem) for text in texts]
        results = await tqdm.gather(*tasks, ascii=True, total=len(texts))

        return [r for r in results if not isinstance(r, Exception)]

    async def process_pending_embeddings(self):
        movies = self.db.get_movies_needing_embeddings()
        texts = [text for _, text in movies]
        embeddings = await self.process_texts(texts)

        for (movie_id, _), embedding in zip(movies, embeddings):
            self.db.add_movie_embedding(movie_id, embedding)

    def find_similar_movies(self, description: str, limit: int = 5):
        embedding = self.sync_embed(description)
        return self.db.get_similar_movies(embedding, limit)
