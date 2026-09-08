import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.api_client import KovaaksApiClient
from core.playlist_service import PlaylistService

def test_pipeline():
    client = KovaaksApiClient()
    print("Fetching progress...")
    prog = client.fetch_player_progress("2336", "76561198444816419")
    print("Fetching sensitivity...")
    sens = client.fetch_sensitivity_distributions("2336")

    service = PlaylistService()
    with tempfile.TemporaryDirectory() as td:
        res = service.process_and_generate_playlist(prog, sens, td, "test_weaknesses")
        print("Generated file:", res["file_path"])
        print("Playlist name:", res["playlist_name"])
        print("Processed Scenarios:")
        for sc in res["scenarios"]:
            print(f" - {sc['name']}: {sc['sens_display']} | score={sc['continuous_score']}")
        
        with open(res["file_path"], "r", encoding="utf-8") as f:
            pl_data = json.load(f)
            assert pl_data["playlistName"] == "test_weaknesses"
            assert len(pl_data["scenarioList"]) == 5
            for item in pl_data["scenarioList"]:
                assert item["playCount"] == 5
                assert "scenarioName" in item
            print("All playlist assertions passed successfully!")

if __name__ == "__main__":
    test_pipeline()
