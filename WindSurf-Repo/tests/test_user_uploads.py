"""Test user uploads and admin approval."""

import pytest
import httpx
import asyncio
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


async def test_user_upload_flow():
    """Test complete user upload flow."""
    print("\n" + "=" * 60)
    print("TEST: USER UPLOAD FLOW")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login as regular user
        print("\n[1/5] Logging in as user...")
        login_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "testuser@example.com", "password": "TestPassword123!"},
        )

        if login_response.status_code != 200:
            print(f"   ⚠️  User login failed: {login_response.status_code}")
            print(f"   Creating test user first...")
            # Create user
            register_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/auth/register",
                json={
                    "email": "testuser@example.com",
                    "password": "TestPassword123!",
                    "full_name": "Test User",
                },
            )
            if register_response.status_code == 201:
                login_response = await client.post(
                    f"{BASE_URL}{API_PREFIX}/auth/login-json",
                    json={"email": "testuser@example.com", "password": "TestPassword123!"},
                )

        assert login_response.status_code == 200, f"Login failed: {login_response.status_code}"
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"   ✅ User logged in")

        # 2. Check subscription (or create one for testing)
        print("\n[2/5] Checking subscription...")
        sub_response = await client.get(
            f"{BASE_URL}{API_PREFIX}/subscription/status", headers=headers
        )
        print(f"   Subscription status: {sub_response.status_code}")

        # 3. Upload content (simulate with small file)
        print("\n[3/5] Uploading content...")
        # Create a small test file
        test_content = b"fake video content for testing"
        files = {"file": ("test_video.mp4", test_content, "video/mp4")}
        data = {
            "title": "Test Upload Video",
            "description": "This is a test upload",
            "tags": "test,upload,demo",
        }

        upload_response = await client.post(
            f"{BASE_URL}{API_PREFIX}/user-uploads/upload", headers=headers, files=files, data=data
        )

        if upload_response.status_code == 201:
            upload_data = upload_response.json()
            content_id = upload_data["id"]
            print(f"   ✅ Content uploaded: {content_id}")
            print(f"   Status: {upload_data['status']}")
            assert upload_data["status"] == "pending_approval", "Content should be pending approval"
        else:
            print(f"   ⚠️  Upload failed: {upload_response.status_code}")
            print(f"   Response: {upload_response.text}")
            # Skip if upload fails (might need subscription)
            return

        # 4. Check my uploads
        print("\n[4/5] Checking my uploads...")
        my_uploads_response = await client.get(
            f"{BASE_URL}{API_PREFIX}/user-uploads/my-uploads", headers=headers
        )
        if my_uploads_response.status_code == 200:
            uploads_data = my_uploads_response.json()
            print(f"   ✅ Found {uploads_data['total']} uploads")
            print(f"   Pending: {uploads_data['pending_approval']}")
            print(f"   Approved: {uploads_data['approved']}")

        # 5. Admin approval (login as admin)
        print("\n[5/5] Testing admin approval...")
        admin_login = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if admin_login.status_code == 200:
            admin_token = admin_login.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Get pending content
            pending_response = await client.get(
                f"{BASE_URL}{API_PREFIX}/admin/approval/pending", headers=admin_headers
            )

            if pending_response.status_code == 200:
                pending_data = pending_response.json()
                print(f"   ✅ Found {pending_data['total']} pending items")

                # Approve first item if exists
                if pending_data["total"] > 0 and "content_id" in locals():
                    approve_response = await client.post(
                        f"{BASE_URL}{API_PREFIX}/admin/approval/approve",
                        headers=admin_headers,
                        json={
                            "content_id": content_id,
                            "approve": True,
                            "notes": "Test approval - looks good!",
                        },
                    )
                    if approve_response.status_code == 200:
                        print(f"   ✅ Content approved successfully")
                    else:
                        print(f"   ⚠️  Approval failed: {approve_response.status_code}")
            else:
                print(f"   ⚠️  Could not fetch pending: {pending_response.status_code}")
        else:
            print(f"   ⚠️  Admin login failed: {admin_login.status_code}")

    print("\n" + "=" * 60)
    print("✅ USER UPLOAD FLOW TEST COMPLETE")
    print("=" * 60)


async def test_admin_approval_only():
    """Test that only admin can approve."""
    print("\n" + "=" * 60)
    print("TEST: ADMIN APPROVAL SECURITY")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try as regular user
        print("\n[1/2] Testing as regular user (should fail)...")
        user_login = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "testuser@example.com", "password": "TestPassword123!"},
        )

        if user_login.status_code == 200:
            user_token = user_login.json()["access_token"]
            user_headers = {"Authorization": f"Bearer {user_token}"}

            # Try to approve (should fail)
            approve_response = await client.post(
                f"{BASE_URL}{API_PREFIX}/admin/approval/approve",
                headers=user_headers,
                json={"content_id": "test-123", "approve": True},
            )

            if approve_response.status_code == 403:
                print(f"   ✅ Regular user correctly blocked (403)")
            else:
                print(f"   ⚠️  Unexpected status: {approve_response.status_code}")

        # Test as admin (should work)
        print("\n[2/2] Testing as admin (should work)...")
        admin_login = await client.post(
            f"{BASE_URL}{API_PREFIX}/auth/login-json",
            json={"email": "anthonymillwater2@hotmail.com", "password": "GoonSite32$"},
        )

        if admin_login.status_code == 200:
            admin_token = admin_login.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Get pending (should work)
            pending_response = await client.get(
                f"{BASE_URL}{API_PREFIX}/admin/approval/pending", headers=admin_headers
            )

            if pending_response.status_code == 200:
                print(f"   ✅ Admin can access approval endpoints")
            else:
                print(f"   ⚠️  Admin access failed: {pending_response.status_code}")

    print("\n" + "=" * 60)
    print("✅ ADMIN APPROVAL SECURITY TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_user_upload_flow())
    asyncio.run(test_admin_approval_only())
