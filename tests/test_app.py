"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state
    for name in activities:
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns 200 status code"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that GET /activities returns a dictionary"""
        response = client.get("/activities")
        assert isinstance(response.json(), dict)
    
    def test_get_activities_contains_expected_fields(self, client):
        """Test that activities contain expected fields"""
        response = client.get("/activities")
        activities_data = response.json()
        
        for activity_name, activity_data in activities_data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_get_activities_contains_all_activities(self, client):
        """Test that all expected activities are returned"""
        response = client.get("/activities")
        activities_data = response.json()
        
        expected_activities = [
            "Chess Club", "Programming Class", "Gym Class", 
            "Basketball Team", "Soccer Club", "Art Club", 
            "Drama Club", "Debate Team", "Math Club"
        ]
        
        for activity_name in expected_activities:
            assert activity_name in activities_data


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant(self, client, reset_activities):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Basketball Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "newstudent@mergington.edu" in response.json()["message"]
    
    def test_signup_updates_participants_list(self, client, reset_activities):
        """Test that signup updates the participants list"""
        email = "test@mergington.edu"
        client.post(f"/activities/Soccer Club/signup?email={email}")
        
        response = client.get("/activities")
        activity = response.json()["Soccer Club"]
        assert email in activity["participants"]
    
    def test_signup_duplicate_participant_fails(self, client, reset_activities):
        """Test that signing up twice fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Art Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Art Club/signup?email={email}")
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_signup_existing_participant_fails(self, client, reset_activities):
        """Test that existing participant cannot sign up again"""
        # Chess Club already has michael@mergington.edu
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]


class TestUnregister:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        # Chess Club has michael@mergington.edu
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        assert "michael@mergington.edu" in response.json()["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister removes participant from list"""
        email = "michael@mergington.edu"
        
        # Verify participant is in list
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]
        
        # Unregister
        client.post(f"/activities/Chess Club/unregister?email={email}")
        
        # Verify participant is removed
        response = client.get("/activities")
        assert email not in response.json()["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_unregister_nonexistent_participant_fails(self, client, reset_activities):
        """Test that unregistering nonexistent participant fails"""
        response = client.post(
            "/activities/Basketball Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_twice_fails(self, client, reset_activities):
        """Test that unregistering twice fails"""
        email = "michael@mergington.edu"
        
        # First unregister should succeed
        response1 = client.post(f"/activities/Chess Club/unregister?email={email}")
        assert response1.status_code == 200
        
        # Second unregister should fail
        response2 = client.post(f"/activities/Chess Club/unregister?email={email}")
        assert response2.status_code == 400
        assert "not signed up" in response2.json()["detail"]


class TestSignupAndUnregister:
    """Integration tests for signup and unregister workflows"""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test full workflow of signing up and then unregistering"""
        email = "workflow@mergington.edu"
        activity = "Drama Club"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify participant is in list
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify participant is removed
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
    
    def test_signup_unregister_signup_again(self, client, reset_activities):
        """Test that participant can sign up again after unregistering"""
        email = "workflow2@mergington.edu"
        activity = "Debate Team"
        
        # First signup
        client.post(f"/activities/{activity}/signup?email={email}")
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        client.post(f"/activities/{activity}/unregister?email={email}")
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        
        # Sign up again should succeed
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify participant is in list again
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
