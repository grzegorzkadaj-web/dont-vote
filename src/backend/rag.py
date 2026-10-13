from operator import itemgetter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from src.backend.config import settings
from src.backend.parties import PARTY_CONFIGS
from src.backend.schemas import AskResponse, PartyAnswer, SourceItem

ANSWER_PROMPT = ChatPromptTemplate.from_template(
    """Jesteś asystentem porównującym programy partii politycznych.
Korzystaj WYŁĄCZNIE z poniższego kontekstu.
Jeśli w kontekście nie ma odpowiedzi, napisz to wprost.

Kontekst:
{context}

Pytanie:
{question}

Napisz odpowiedź po polsku. Odpowiedź ma być konkretna i bez spekulacji."""
)


def format_docs_with_sources(
    docs_with_scores: list[tuple],
) -> tuple[str, list[SourceItem]]:
    parts: list[str] = []
    sources: list[SourceItem] = []
    for document, score in docs_with_scores:
        url = (
            document.metadata.get("source")
            or document.metadata.get("url")
            or document.metadata.get("programme_url")
            or "brak-źródła"
        )
        snippet = document.page_content.strip().replace("\n", " ")
        snippet_short = snippet[:280] + ("..." if len(snippet) > 280 else "")
        parts.append(f"[{url}] {document.page_content}")
        sources.append(
            SourceItem(
                url=url,
                score=float(score),
                snippet=snippet_short,
            )
        )
    return "\n\n".join(parts), sources


class RAGService:
    def __init__(self) -> None:
        self.embeddings = OpenAIEmbeddings(model=settings.embeddings_model)
        self.llm = ChatOpenAI(model=settings.chat_model)

        self.vectorstores = {
            party_key: PineconeVectorStore(
                index_name=config.index_name,
                embedding=self.embeddings,
            )
            for party_key, config in PARTY_CONFIGS.items()
        }

    def _validate_parties(self, parties: list[str] | None) -> list[str]:
        if not parties:
            return list(PARTY_CONFIGS.keys())
        invalid = [party for party in parties if party not in PARTY_CONFIGS]
        if invalid:
            raise ValueError(f"Unknown parties: {', '.join(invalid)}")
        return parties

    def ask(self, question: str, parties: list[str] | None = None) -> AskResponse:
        selected_parties = self._validate_parties(parties)
        answers: list[PartyAnswer] = []

        for party_key in selected_parties:
            party = PARTY_CONFIGS[party_key]
            docs_with_scores = self.vectorstores[
                party_key
            ].similarity_search_with_score(
                query=question,
                k=settings.retrieval_k,
            )
            context, sources = format_docs_with_sources(docs_with_scores)
            chain = (
                RunnablePassthrough.assign(
                    context=itemgetter("context"),
                    question=itemgetter("question"),
                )
                | ANSWER_PROMPT
                | self.llm
                | StrOutputParser()
            )
            answer_text = chain.invoke({"question": question, "context": context})
            answers.append(
                PartyAnswer(
                    party_key=party_key,
                    party_display_name=party.display_name,
                    answer=answer_text,
                    sources=sources,
                )
            )

        return AskResponse(question=question, answers=answers)
