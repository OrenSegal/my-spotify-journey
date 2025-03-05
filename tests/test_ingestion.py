import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.duckdb_helper import get_connection_with_retry, create_tables_if_needed
import duckdb
import os
import json
from pathlib import Path

# Use TestClient with the FastAPI app
client = TestClient(app)

# Fixture for a temporary database connection
@pytest.fixture(scope="module")
def test_db():
    db_path = "test_spotify.duckdb"
    if os.path.exists(db_path):  # Ensure clean start
        os.remove(db_path)
    conn = duckdb.connect(db_path)
    create_tables_if_needed(conn)  # Use the consolidated create_tables_if_needed function
    yield conn
    conn.close()
    if os.path.exists(db_path): #teardown
        os.remove(db_path)

# Fixture for sample data (streaming history)
@pytest.fixture
def sample_streaming_data():
    return [
        {
            "ts": "2024-05-28T10:00:00Z",
            "platform": "ios",
            "ms_played": 60000,
            "master_metadata_track_name": "Test Track",
            "master_metadata_album_artist_name": "Test Artist",
            "master_metadata_album_album_name": "Test Album",
            "spotify_track_uri": "spotify:track:test_track_uri",
            "reason_start": "trackdone",
            "reason_end": "trackdone",
            "skipped": False,
            "conn_country": "US"
        }
    ]

# Fixture for sample data (track metadata)
@pytest.fixture
def sample_metadata():
  return """track,artist,track_uri,track_popularity,album_release_date,album,duration_ms,explicit,album_type,total_tracks,genres,artist_popularity,artist_uri,artist_followers
Test Track,Test Artist,spotify:track:test_track_uri,50,2024-01-01,Test Album,180000,False,album,10,"['test genre']",70,spotify:artist:test,1000
"""

# Test streaming history ingestion
def test_ingest_streaming_history_success(test_db, sample_streaming_data):
    # Prepare the file
    json_data = json.dumps(sample_streaming_data).encode('utf-8')
    files = {"file": ("streaming_history.json", json_data, "application/json")}
    response = client.post("/ingest/streaming-history", files=files)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Inserted 1 rows."}


    # Verify data in the database
    result = test_db.execute("SELECT * FROM streaming_history").fetchall()
    assert len(result) == 1
    assert result[0][4] == "Test Track"  # Check track name

def test_ingest_streaming_history_invalid_json(test_db):
    files = {"file": ("invalid.json", b"invalid json", "application/json")}
    response = client.post("/ingest/streaming-history", files=files)
    assert response.status_code == 400  # Expecting a 400 Bad Request

def test_ingest_track_metadata_success(test_db, sample_metadata):
     # Use a BytesIO object to simulate a file
    from io import BytesIO
    csv_data = BytesIO(sample_metadata.encode('utf-8'))

    files = {'file': ('metadata.csv', csv_data, 'text/csv')}
    response = client.post("/ingest/track-metadata", files=files)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

     # Verify data insertion
    result = test_db.execute("SELECT * FROM track_metadata").fetchall()
    assert len(result) == 1
    assert result[0][0] == 'spotify:track:test_track_uri'

def test_ingest_track_metadata_invalid_csv(test_db):
    files = {"file": ("invalid.csv", b"invalid csv", "text/csv")}
    response = client.post("/ingest/track-metadata", files=files)
    assert response.status_code == 400