"""
debug_ado.py — Run this to diagnose Azure DevOps connection issues.
python debug_ado.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.services.azure_devops import AzureDevOpsService
import requests

ado = AzureDevOpsService()

print("\n=== CONFIG CHECK ===")
print(f"Org:          {ado.org}")
print(f"Project:      {ado.project}")
print(f"PAT set:      {'YES' if ado.pat else 'NO - MISSING!'}")
print(f"Trigger tag:  {ado.trigger_tag}")
print(f"Done tag:     {ado.done_tag}")

print("\n=== CONNECTION TEST ===")
try:
    resp = requests.get(
        f"{ado.org}/_apis/projects?api-version=7.1",
        auth=ado.auth,
        timeout=10,
    )
    print(f"HTTP Status: {resp.status_code}")
    if resp.status_code == 200:
        projects = [p["name"] for p in resp.json().get("value", [])]
        print(f"Projects found: {projects}")
        if ado.project in projects:
            print(f"✅ Project '{ado.project}' found")
        else:
            print(f"❌ Project '{ado.project}' NOT found — check AZURE_DEVOPS_PROJECT in .env")
    elif resp.status_code == 401:
        print("❌ 401 Unauthorized — PAT is invalid or expired")
    elif resp.status_code == 403:
        print("❌ 403 Forbidden — PAT lacks permissions")
    else:
        print(f"❌ Unexpected: {resp.text[:300]}")
except Exception as e:
    print(f"❌ Connection failed: {e}")

print("\n=== WIQL QUERY TEST ===")
wiql = {
    "query": f"""
        SELECT [System.Id], [System.Title], [System.Tags]
        FROM WorkItems
        WHERE [System.TeamProject] = '{ado.project}'
        ORDER BY [System.CreatedDate] DESC
    """
}
try:
    resp = requests.post(
        f"{ado.base}/wit/wiql?api-version=7.1",
        json=wiql,
        auth=ado.auth,
        timeout=15,
    )
    print(f"HTTP Status: {resp.status_code}")
    if resp.status_code == 200:
        items = resp.json().get("workItems", [])
        print(f"Total work items in project: {len(items)}")

        # Fetch details of first 5
        print("\nFirst 5 work items and their tags:")
        for item in items[:5]:
            wi_id = item["id"]
            detail = ado._get_work_item(str(wi_id))
            if detail:
                print(f"  [{wi_id}] {detail['title'][:50]} | Tags: '{detail['tags']}'")
    else:
        print(f"❌ WIQL failed: {resp.text[:300]}")
except Exception as e:
    print(f"❌ WIQL error: {e}")

print("\n=== TAG SEARCH TEST ===")
wiql_tag = {
    "query": f"""
        SELECT [System.Id], [System.Title], [System.Tags]
        FROM WorkItems
        WHERE [System.TeamProject] = '{ado.project}'
          AND [System.Tags] CONTAINS '{ado.trigger_tag}'
        ORDER BY [System.CreatedDate] DESC
    """
}
try:
    resp = requests.post(
        f"{ado.base}/wit/wiql?api-version=7.1",
        json=wiql_tag,
        auth=ado.auth,
        timeout=15,
    )
    if resp.status_code == 200:
        items = resp.json().get("workItems", [])
        print(f"Work items with tag '{ado.trigger_tag}': {len(items)}")
        for item in items[:5]:
            detail = ado._get_work_item(str(item["id"]))
            if detail:
                print(f"  [{item['id']}] {detail['title'][:50]} | Tags: '{detail['tags']}'")
        if not items:
            print("❌ No items found with this tag")
            print("   → Check the exact tag spelling in Azure DevOps")
            print("   → Tags are case-sensitive in some ADO versions")
    else:
        print(f"❌ {resp.status_code}: {resp.text[:300]}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n=== DONE ===")