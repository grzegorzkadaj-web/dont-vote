import argparse

from src.backend.rag import RAGService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query party programmes stored in Pinecone and print answers."
    )
    parser.add_argument(
        "--question",
        default="Co partie mówią o ochronie zdrowia?",
        help="Question in Polish.",
    )
    parser.add_argument(
        "--parties",
        nargs="*",
        help="Optional party keys (e.g. po psl). Defaults to all parties.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    service = RAGService()
    result = service.ask(question=args.question, parties=args.parties)

    for answer in result.answers:
        print(f"\n[{answer.party_display_name}]")
        print(answer.answer)
        if answer.sources:
            print("Źródła:")
            for source in answer.sources:
                print(f"- {source.url} (score={source.score:.3f})")
