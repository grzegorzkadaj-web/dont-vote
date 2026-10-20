import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.votings import expand_search_terms, SejmVotingService


def test_expand_search_terms():
    terms_in_vitro = expand_search_terms("in vitro")
    assert "in vitro" in terms_in_vitro
    assert any("niepłodn" in t for t in terms_in_vitro)

    terms_zdrowie = expand_search_terms("ochrona zdrowia")
    assert any("zdrowi" in t or "zdrowia" in t for t in terms_zdrowie)

    terms_podatki = expand_search_terms("podatki")
    assert any("podatk" in t for t in terms_podatki)


def test_sejm_voting_service():
    service = SejmVotingService(current_term=10)
    acts = service.search_acts_and_votes("zdrowie", limit=2)
    assert isinstance(acts, list)
    assert len(acts) > 0

    first = acts[0]
    assert "act_name" in first
    assert "short_description" in first
    assert "sitting" in first
    assert "voting_number" in first
    assert "total_votes" in first
    assert "parties" in first
    assert len(first["parties"]) > 0

    first_party = first["parties"][0]
    assert "club_id" in first_party
    assert "club_name" in first_party
    assert "yes" in first_party
    assert "no" in first_party
    assert "abstain" in first_party
    assert "stance" in first_party
    assert "percent_yes" in first_party


def test_api_votings_search_post():
    client = TestClient(app)
    response = client.post("/api/votings/search", json={"query": "zdrowie", "limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "zdrowie"
    assert data["results_count"] > 0
    assert len(data["acts"]) > 0

    act = data["acts"][0]
    assert "act_name" in act
    assert "short_description" in act
    assert "parties" in act


def test_api_votings_search_get():
    client = TestClient(app)
    response = client.get("/api/votings/search?q=podatki&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "podatki"
    assert data["results_count"] > 0


def test_api_votings_validation_error():
    client = TestClient(app)
    # Query too short
    response = client.post("/api/votings/search", json={"query": "a", "limit": 2})
    assert response.status_code == 422


if __name__ == "__main__":
    print("Running test_expand_search_terms...")
    test_expand_search_terms()
    print("Running test_sejm_voting_service...")
    test_sejm_voting_service()
    print("Running test_api_votings_search_post...")
    test_api_votings_search_post()
    print("Running test_api_votings_search_get...")
    test_api_votings_search_get()
    print("Running test_api_votings_validation_error...")
    test_api_votings_validation_error()
    print("All tests passed successfully!")
